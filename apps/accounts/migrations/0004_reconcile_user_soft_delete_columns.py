from django.db import migrations


EXPECTED_COLUMNS = {
    'id': ('bigint', 'NO', None, 'auto_increment'),
    'password': ('varchar(128)', 'NO', None, ''),
    'last_login': ('datetime(6)', 'YES', None, ''),
    'is_superuser': ('tinyint(1)', 'NO', None, ''),
    'email': ('varchar(254)', 'NO', None, ''),
    'email_verified': ('tinyint(1)', 'NO', None, ''),
    'is_first_login': ('tinyint(1)', 'NO', None, ''),
    'first_name': ('varchar(100)', 'NO', None, ''),
    'middle_name': ('varchar(100)', 'NO', None, ''),
    'last_name': ('varchar(100)', 'NO', None, ''),
    'contact_num': ('varchar(11)', 'NO', None, ''),
    'role': ('varchar(10)', 'NO', None, ''),
    'is_active': ('tinyint(1)', 'NO', None, ''),
    'is_staff': ('tinyint(1)', 'NO', None, ''),
    'profile_picture': ('varchar(100)', 'YES', None, ''),
    'date_joined': ('datetime(6)', 'NO', None, ''),
}


def validate_pre_reconciliation_schema(apps, schema_editor):
    """Refuse to alter a database other than the inspected legacy schema."""
    connection = schema_editor.connection
    if connection.vendor != 'mysql':
        raise RuntimeError(
            'This reconciliation migration is only valid for the confirmed MySQL schema.'
        )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
            """,
            ['accounts_user'],
        )
        actual_columns = {
            name: (column_type, is_nullable, column_default, extra)
            for name, column_type, is_nullable, column_default, extra in cursor.fetchall()
        }

    if actual_columns != EXPECTED_COLUMNS:
        raise RuntimeError(
            'accounts_user does not match the confirmed pre-reconciliation schema; '
            'no columns were added. Expected exactly the legacy accounts_user columns '
            'without is_deleted or deleted_at.'
        )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_database_seeder'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    validate_pre_reconciliation_schema,
                    migrations.RunPython.noop,
                ),
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE `accounts_user`
                            ADD COLUMN `is_deleted` tinyint(1) NOT NULL DEFAULT 0,
                            ADD COLUMN `deleted_at` datetime(6) NULL DEFAULT NULL
                    """,
                    reverse_sql=None,
                ),
            ],
            state_operations=[],
        ),
    ]
