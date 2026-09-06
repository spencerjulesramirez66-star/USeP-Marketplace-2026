from django.db import migrations, models


PROGRAMS = {
    'beed': 'Bachelor of Elementary Education (BEEd)',
    'beced': 'Bachelor of Early Childhood Education (BECEd)',
    'bsned': 'Bachelor of Special Needs Education (BSNEd)',
    'bsed': 'Bachelor of Secondary Education (BSEd)',
    'btvted': 'Bachelor of Technical-Vocational Teacher Education (BTVTEd)',
    'bsit': 'Bachelor of Science in Information Technology (BSIT)',
}

MAJORS = {
    'bsed': ['Major in English', 'Major in Filipino', 'Major in Mathematics'],
    'btvted': ['Major in Agricultural Crops Technology', 'Major in Animal Production'],
}


def normalize_profiles(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    College = apps.get_model('accounts', 'College')
    Program = apps.get_model('accounts', 'Program')
    Major = apps.get_model('accounts', 'Major')
    StudentProfile = apps.get_model('accounts', 'StudentProfile')
    StaffProfile = apps.get_model('accounts', 'StaffProfile')

    college, _ = College.objects.get_or_create(college_name='USeP Academic Programs')
    programs = {}
    for key, name in PROGRAMS.items():
        program = Program.objects.filter(program_name=name).first()
        if not program:
            legacy_names = {
                'beed': 'Bachelor of Science in Elementary Education',
                'beced': 'Bachelor of Science in Early Childhood Education',
                'bsned': 'Bachelor of Science in Special Needs Education',
                'bsed': 'Bachelor of Secondary Education',
                'btvted': 'Bachelor of Science in Technical-Vocational Teacher Education',
                'bsit': 'Bachelor of Science in Information Technology',
            }
            program = Program.objects.filter(program_name=legacy_names[key]).first()
        if program:
            program.program_name = name
            program.save(update_fields=['program_name'])
        else:
            program = Program.objects.create(program_name=name, college=college)
        programs[key] = program

    majors = {}
    for program_key, names in MAJORS.items():
        for name in names:
            major = Major.objects.filter(program=programs[program_key], major_name=name).first()
            if not major:
                legacy_name = 'Math' if name == 'Major in Mathematics' else name.removeprefix('Major in ')
                major = Major.objects.filter(program=programs[program_key], major_name=legacy_name).first()
            if major:
                major.major_name = name
                major.save(update_fields=['major_name'])
            else:
                major = Major.objects.create(program=programs[program_key], major_name=name)
            majors[name] = major

    # Existing student records are moved into the approved catalog.
    bsit = programs['bsit']
    StudentProfile.objects.all().update(program=bsit, major=None)

    # Every existing account must have one profile classification. Existing
    # student/staff profiles are preserved; unclassified accounts default to students.
    for user in User.objects.all():
        has_student = StudentProfile.objects.filter(user=user).exists()
        has_staff = StaffProfile.objects.filter(user=user).exists()
        if not has_student and not has_staff:
            StudentProfile.objects.create(
                user=user,
                student_id=f'B{user.pk:08d}',
                year_level=None,
                program=bsit,
                major=None,
            )


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0006_user_is_seller'),
    ]

    operations = [
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
        migrations.RunPython(normalize_profiles, migrations.RunPython.noop),
    ]