from django.db import migrations
from django.contrib.auth.hashers import make_password


def create_test_users(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    StudentProfile = apps.get_model("accounts", "StudentProfile")
    StaffProfile = apps.get_model("accounts", "StaffProfile")
    Major = apps.get_model("accounts", "Major")
    Campus = apps.get_model("accounts", "Campus")

<<<<<<< HEAD
    # Get existing university data
=======
>>>>>>> 6fe02047874f2a41b2024f6c526d69b183b30d75
    major = Major.objects.first()
    campus = Campus.objects.first()

    if not major:
        raise RuntimeError(
            "No Major exists. Run the university data seeder first."
        )

    if not campus:
        raise RuntimeError(
            "No Campus exists. Run the university data seeder first."
        )

    # -------------------------
    # STUDENT TEST ACCOUNT
    # -------------------------

    student, created = User.objects.get_or_create(
        email="spejdjdjjd@gmail.com",
        defaults={
            "password": make_password("TestPassword123!"),
            "email_verified": False,
            "is_first_login": True,
            "first_name": "Test",
            "middle_name": "",
            "last_name": "Student",
            "contact_num": "09123456781",
            "role": "USER",
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
        },
    )

    if created:
        StudentProfile.objects.create(
            user=student,
            student_id="TEST000001",
            year_level="3",
            major=major,
        )

    # -------------------------
    # STAFF TEST ACCOUNT
    # -------------------------

    staff, created = User.objects.get_or_create(
        email="spencerjulesramirez66@gmail.com",
        defaults={
            "password": make_password("TestPassword123!"),
            "email_verified": False,
            "is_first_login": True,
            "first_name": "Spencer",
            "middle_name": "",
            "last_name": "Ramirez",
            "contact_num": "09123456782",
            "role": "USER",
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
        },
    )

    if created:
        StaffProfile.objects.create(
            user=staff,
            staff_id="TEST001",
            staff_type="TEACHING",
            campus=campus,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_emailotp"),
    ]

    operations = [
        migrations.RunPython(create_test_users),
    ]