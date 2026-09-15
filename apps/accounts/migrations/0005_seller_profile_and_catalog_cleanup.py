import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


# Old program/major names (from the 0002 seeder) -> normalized display names.
PROGRAM_NAMES = {
    'Bachelor of Science in Elementary Education': 'Bachelor of Elementary Education (BEEd)',
    'Bachelor of Science in Early Childhood Education': 'Bachelor of Early Childhood Education (BECEd)',
    'Bachelor of Science in Special Needs Education': 'Bachelor of Special Needs Education (BSNEd)',
    'Bachelor of Secondary Education': 'Bachelor of Secondary Education (BSEd)',
    'Bachelor of Science in Technical-Vocational Teacher Education': 'Bachelor of Technical-Vocational Teacher Education (BTVTEd)',
    'Bachelor of Science in Information Technology': 'Bachelor of Science in Information Technology (BSIT)',
}

MAJOR_NAMES = {
    'Math': 'Major in Mathematics',
    'English': 'Major in English',
    'Animal Production': 'Major in Animal Production',
}


def normalize_catalog_and_profiles(apps, schema_editor):
    Program = apps.get_model('accounts', 'Program')
    Major = apps.get_model('accounts', 'Major')
    User = apps.get_model('accounts', 'User')
    StudentProfile = apps.get_model('accounts', 'StudentProfile')
    StaffProfile = apps.get_model('accounts', 'StaffProfile')

    # Bulk-rename in place instead of fetch-then-save per row.
    for old_name, new_name in PROGRAM_NAMES.items():
        Program.objects.filter(program_name=old_name).update(program_name=new_name)

    for old_name, new_name in MAJOR_NAMES.items():
        Major.objects.filter(major_name=old_name).update(major_name=new_name)

    bsit = Program.objects.filter(
        program_name='Bachelor of Science in Information Technology (BSIT)'
    ).first()

    # All existing student records move onto the BSIT program with no major set.
    if bsit:
        StudentProfile.objects.update(program=bsit, major=None)

    # Any account without a student or staff profile defaults to a student.
    # Computed as two set lookups instead of a query-per-user loop.
    classified_user_ids = set(StudentProfile.objects.values_list('user_id', flat=True)) | set(
        StaffProfile.objects.values_list('user_id', flat=True)
    )

    for user in User.objects.exclude(id__in=classified_user_ids):
        StudentProfile.objects.create(
            user=user,
            student_id=f'B{user.pk:08d}',
            program=bsit,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_seed_test_users'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailotp',
            name='purpose',
            field=models.CharField(
                choices=[
                    ('EMAIL_VERIFICATION', 'Email Verification'),
                    ('PASSWORD_RESET', 'Password Reset'),
                ],
                default='EMAIL_VERIFICATION',
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name='studentprofile',
            name='major',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.PROTECT,
                related_name='students',
                to='accounts.major',
            ),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='program',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.PROTECT,
                related_name='enrolled_students',
                to='accounts.program',
            ),
        ),
        migrations.CreateModel(
            name='SellerProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_verified', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='seller_profile',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
        migrations.RunPython(normalize_catalog_and_profiles, migrations.RunPython.noop),
    ]