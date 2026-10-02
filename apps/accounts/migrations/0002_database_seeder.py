from django.db import migrations


def seed_university_data(apps, schema_editor):
    Campus = apps.get_model('accounts', 'Campus')
    College = apps.get_model('accounts', 'College')
    Program = apps.get_model('accounts', 'Program')
    Major = apps.get_model('accounts', 'Major')

    # ============================================================
    # CAMPUSES
    # ============================================================

    tagum, _ = Campus.objects.get_or_create(
        campus_code='TA',
        defaults={
            'campus_name': 'Tagum Campus'
        }
    )

    mabini, _ = Campus.objects.get_or_create(
        campus_code='MA',
        defaults={
            'campus_name': 'Mabini Campus'
        }
    )

    obrero, _ = Campus.objects.get_or_create(
        campus_code='OB',
        defaults={
            'campus_name': 'Obrero Campus'
        }
    )

    mintal, _ = Campus.objects.get_or_create(
        campus_code='MI',
        defaults={
            'campus_name': 'Mintal Campus'
        }
    )

    # ============================================================
    # COLLEGES
    # ============================================================

    coe, _ = College.objects.get_or_create(
        college_name='College of Engineering',
        defaults={
            'campus': tagum
        }
    )

    ctet, _ = College.objects.get_or_create(
        college_name='College of Teacher Education and Technology',
        defaults={
            'campus': tagum
        }
    )

    # ============================================================
    # PROGRAMS
    # ============================================================

    bsabe, _ = Program.objects.get_or_create(
        program_name='Bachelor of Science in Agricultural and Biosystems Engineering',
        college=coe
    )

    bced, _ = Program.objects.get_or_create(
        program_name='Bachelor of Science in Early Childhood Education',
        college=ctet
    )

    beed, _ = Program.objects.get_or_create(
        program_name='Bachelor of Science in Elementary Education',
        college=ctet
    )

    bsed, _ = Program.objects.get_or_create(
        program_name='Bachelor of Science in Secondary Education',
        college=ctet
    )

    bsned, _ = Program.objects.get_or_create(
        program_name='Bachelor of Science in Special Needs Education',
        college=ctet
    )

    btvted, _ = Program.objects.get_or_create(
        program_name='Bachelor of Science in Technical-Vocational Teacher Education',
        college=ctet
    )

    bsit, _ = Program.objects.get_or_create(
        program_name='Bachelor of Science in Information Technology',
        college=ctet
    )

    # ============================================================
    # MAJORS
    # ============================================================

    Major.objects.get_or_create(
        major_name='Major in Land and Water Resources Engineering',
        program=bsabe
    )

    Major.objects.get_or_create(
        major_name='Machinery and Power Engineering',
        program=bsabe
    )

    Major.objects.get_or_create(
        major_name='Process Engineering',
        program=bsabe
    )

    Major.objects.get_or_create(
        major_name='Structures and Environment Engineering',
        program=bsabe
    )

    Major.objects.get_or_create(
        major_name='Animal Production',
        program=btvted
    )

    Major.objects.get_or_create(
        major_name='Math',
        program=bsed
    )

    Major.objects.get_or_create(
        major_name='English',
        program=bsed
    )

    Major.objects.get_or_create(
        major_name='Information Security',
        program=bsit
    )


def remove_university_data(apps, schema_editor):
    Campus = apps.get_model('accounts', 'Campus')
    College = apps.get_model('accounts', 'College')

    Major = apps.get_model('accounts', 'Major')
    Program = apps.get_model('accounts', 'Program')

    # Delete colleges first.
    # Their related programs and majors will cascade.
    College.objects.filter(
        college_name__in=[
            'College of Engineering',
            'College of Teacher Education and Technology',
        ]
    ).delete()

    Campus.objects.filter(
        campus_code__in=[
            'TA',
            'MA',
            'OB',
            'MI',
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            seed_university_data,
            remove_university_data,
        ),
    ]