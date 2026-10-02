from django.db import migrations


# ============================================================
# COLLEGES
# ============================================================

COE = "College of Engineering"
CTET = "College of Teacher Education and Technology"


# ============================================================
# PROGRAMS
# ============================================================

BSABE = "Bachelor of Science in Agricultural and Biosystems Engineering"
BCED = "Bachelor of Science in Early Childhood Education"
BEED = "Bachelor of Science in Elementary Education"
BSED = "Bachelor of Science in Secondary Education"
BSNED = "Bachelor of Science in Special Needs Education"
BTVTED = "Bachelor of Science in Technical-Vocational Teacher Education"
BSIT = "Bachelor of Science in Information Technology"


# ============================================================
# MAJORS
# ============================================================

LAND_WATER = "Major in Land and Water Resources Engineering"
MACHINERY_POWER = "Machinery and Power Engineering"
PROCESS = "Process Engineering"
STRUCTURES_ENVIRONMENT = "Structures and Environment Engineering"

ANIMAL_PRODUCTION = "Animal Production"

MATH = "Math"
ENGLISH = "English"

INFORMATION_SECURITY = "Information Security"


# ============================================================
# STUDENT PROFILES
# ============================================================

STUDENT_PROFILES = {

    "spejdjdjjd@gmail.com": {
        "student_id": "TEST000001",
        "year_level": "3",
        "college": CTET,
        "program": BSIT,
        "major": INFORMATION_SECURITY,
    },

    "spencerjulesramirez66@gmail.com": {
        "student_id": "TEST000003",
        "year_level": "3",
        "college": CTET,
        "program": BSIT,
        "major": INFORMATION_SECURITY,
    },

    "gapbersabal03202500167@usep.edu.ph": {
        "student_id": "2026-00404",
        "year_level": "1",
        "college": CTET,
        "program": BCED,
        "major": None,
    },

    "kblauron03202500307@usep.edu.ph": {
        "student_id": "2026-00413",
        "year_level": "1",
        "college": CTET,
        "program": BCED,
        "major": None,
    },
}


def seed_student_profiles(apps, schema_editor):

    User = apps.get_model("accounts", "User")
    College = apps.get_model("accounts", "College")
    Program = apps.get_model("accounts", "Program")
    Major = apps.get_model("accounts", "Major")
    StudentProfile = apps.get_model("accounts", "StudentProfile")

    for email, fields in STUDENT_PROFILES.items():

        user = User.objects.filter(
            email=email
        ).first()

        if not user:
            continue

        # --------------------------------------------------------
        # College
        # --------------------------------------------------------

        college = College.objects.filter(
            college_name=fields["college"]
        ).first()

        if not college:
            raise RuntimeError(
                f"College not found: {fields['college']}"
            )

        # --------------------------------------------------------
        # Program
        # --------------------------------------------------------

        program = Program.objects.filter(
            program_name=fields["program"],
            college=college
        ).first()

        if not program:
            raise RuntimeError(
                f"Program not found: {fields['program']} "
                f"under college: {fields['college']}"
            )

        # --------------------------------------------------------
        # Major
        # --------------------------------------------------------

        # --------------------------------------------------------
# Major
# --------------------------------------------------------

        major = None

        if fields["major"] is not None:

            major = Major.objects.filter(
                major_name=fields["major"],
                program=program
            ).first()

            if not major:
                raise RuntimeError(
                    f"Major not found: {fields['major']} "
                    f"under program: {fields['program']}"
                )

        # --------------------------------------------------------
        # Student Profile
        # --------------------------------------------------------

        StudentProfile.objects.update_or_create(
            user=user,
            defaults={
                "student_id": fields["student_id"],
                "year_level": fields["year_level"],
                "program": program,
                "major": major,
            },
        )


def remove_student_profiles(apps, schema_editor):

    StudentProfile = apps.get_model(
        "accounts",
        "StudentProfile"
    )

    StudentProfile.objects.filter(
        user__email__in=list(STUDENT_PROFILES)
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_seller_profile_and_catalog_cleanup"),
    ]

    operations = [
        migrations.RunPython(
            seed_student_profiles,
            remove_student_profiles,
        ),
    ]
