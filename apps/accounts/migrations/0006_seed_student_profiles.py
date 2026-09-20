from django.db import migrations


PROGRAM_NAME = 'Bachelor of Science in Information Technology (BSIT)'
LEGACY_PROGRAM_NAME = 'Bachelor of Science in Information Technology'

# Existing accounts (from 0004) -> their StudentProfile fields.
# student_id: max 10 chars, unique.
# year_level: '1'..'6' per YearLevel choices.
# major: None, since the BSIT profiles carry no major.
STUDENT_PROFILES = {
    'spejdjdjjd@gmail.com': {
        'student_id': 'TEST000001',
        'year_level': '3',
    },
    'biratacador03202400139@usep.edu.ph': {
        'student_id': 'TEST000002',
        'year_level': '3',
    },
}


def seed_student_profiles(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    Program = apps.get_model('accounts', 'Program')
    StudentProfile = apps.get_model('accounts', 'StudentProfile')

    program = (
        Program.objects.filter(program_name=PROGRAM_NAME).first()
        or Program.objects.filter(program_name=LEGACY_PROGRAM_NAME).first()
    )

    if not program:
        raise RuntimeError(
            'BSIT program not found. Run the university data seeder first.'
        )

    for email, fields in STUDENT_PROFILES.items():
        user = User.objects.filter(email=email).first()

        if not user:
            continue

        StudentProfile.objects.update_or_create(
            user=user,
            defaults={
                'student_id': fields['student_id'],
                'year_level': fields['year_level'],
                'program': program,
                'major': None,
            },
        )


def remove_student_profiles(apps, schema_editor):
    StudentProfile = apps.get_model('accounts', 'StudentProfile')

    StudentProfile.objects.filter(
        user__email__in=list(STUDENT_PROFILES)
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_seller_profile_and_catalog_cleanup'),
    ]

    operations = [
        migrations.RunPython(
            seed_student_profiles,
            remove_student_profiles,
        ),
    ]
