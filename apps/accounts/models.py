from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.templatetags.static import static
from django.utils import timezone
from django.core.exceptions import ValidationError
from img_compress import compress_to_webp
from django.db import models

class Roles(models.TextChoices):
    USER = 'USER', 'User'
    ADMIN = 'ADMIN', 'Admin'


class AccountManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        if not password:
            raise ValueError("Superuser must have a password")

        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        extra_fields["is_active"] = True
        extra_fields["role"] = Roles.ADMIN
        extra_fields["is_first_login"] = False

        return self.create_user(
            email=email,
            password=password,
            **extra_fields
        )

class YearLevel(models.TextChoices):
    FIRST_YEAR = '1', '1st Year'
    SECOND_YEAR = '2', '2nd Year'
    THIRD_YEAR = '3', '3rd Year'
    FOURTH_YEAR = '4', '4th Year'
    FIFTH_YEAR = '5', '5th Year'
    SIXTH_YEAR = '6', '6th Year'


class StaffType(models.TextChoices):
    TEACHING = 'TEACHING', 'Teaching Staff'
    NON_TEACHING = 'NON_TEACHING', 'Non-Teaching Staff'


class Campus(models.Model):
    campus_code = models.CharField(
        max_length=2,
        unique=True
    )

    campus_name = models.CharField(
        max_length=150,
        unique=True
    )

    def __str__(self):
        return f'{self.campus_code} - {self.campus_name}'


class College(models.Model):

    college_name = models.CharField(
        max_length=150,
        unique=True
    )

    campus = models.ForeignKey(
        Campus,
        on_delete=models.PROTECT,
        related_name='colleges'
    )

    def __str__(self):
        return self.college_name


class Program(models.Model):
    program_name = models.CharField(
        max_length=150
    )

    college = models.ForeignKey(
        College,
        on_delete=models.CASCADE,
        related_name='programs'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['college', 'program_name'],
                name='unique_program_per_college'
            )
        ]

    def __str__(self):
        return self.program_name


class Major(models.Model):
    major_name = models.CharField(
        max_length=150
    )

    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name='majors'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['program', 'major_name'],
                name='unique_major_per_program'
            )
        ]

    def __str__(self):
        return self.major_name


class User(AbstractBaseUser, PermissionsMixin):

    @property
    def avatar_url(self):
        if self.profile_picture:
            return self.profile_picture.url
        return static('images/default-avatar.jpg')

    @property
    def is_admin(self):
        return self.is_superuser or self.role == Roles.ADMIN

    @property
    def is_seller(self):
        return hasattr(self, 'seller_profile')

    objects = AccountManager()

    # Authentication
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    is_first_login = models.BooleanField(default=True)

    # Personal Information
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(
        max_length=100,
        blank=True
    )
    last_name = models.CharField(max_length=100)

    # Contact
    contact_num = models.CharField(
        max_length=11,
        unique=True
    )

    # System Role
    role = models.CharField(
        max_length=10,
        choices=Roles.choices,
        default=Roles.USER
    )

    # Django permissions
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # Account Information
    profile_picture = models.ImageField(
        upload_to='uploads/',
        blank=True,
        null=True
    )

    date_joined = models.DateTimeField(
        auto_now_add=True
    )

    # Soft deletion
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(
        blank=True,
        null=True
    )

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = [
        "first_name",
        "last_name",
        "contact_num",
    ]

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")

        # Store emails lowercase so login and lookups are case-insensitive.
        if self.email:
            self.email = self.email.lower()

        # Admin-role accounts must be staff, or they can't enter the admin site.
        if self.role == Roles.ADMIN and not self.is_staff:
            self.is_staff = True
            if update_fields is not None:
                update_fields = {*update_fields, "is_staff"}
                kwargs["update_fields"] = update_fields

        saving_picture = update_fields is None or "profile_picture" in update_fields

        if (
            saving_picture
            and self.profile_picture
            and not self.profile_picture.name.lower().endswith('.webp')
        ):
            self.profile_picture = compress_to_webp(
                self.profile_picture,
                max_size=(512, 512),
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.email

    def suspend(self):
        self.is_active = False
        self.save(update_fields=["is_active"])


    def reactivate(self):
        if self.is_deleted:
            raise ValueError("Cannot reactivate a deleted account.")

        self.is_active = True
        self.save(update_fields=["is_active"])


    def soft_delete(self):
        self.is_active = False
        self.is_deleted = True
        self.deleted_at = timezone.now()

        self.save(update_fields=[
            "is_active",
            "is_deleted",
            "deleted_at",
        ])

    def restore(self):
        if not self.is_deleted:
            return

        self.is_deleted = False
        self.deleted_at = None

        # Remain inactive until an admin explicitly reactivates.
        self.is_active = False

        self.save(update_fields=[
            "is_deleted",
            "deleted_at",
            "is_active",
        ])


class StudentProfile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile'
    )

    program = models.ForeignKey(
        Program,
        on_delete=models.PROTECT,
        related_name='enrolled_students',
        blank=True,
        null=True,
    )

    student_id = models.CharField(
        max_length=10,
        unique=True
    )

    year_level = models.CharField(
        max_length=1,
        choices=YearLevel.choices,
        blank=True,
        null=True
    )

    major = models.ForeignKey(
        Major,
        on_delete=models.PROTECT,
        related_name='students',
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.student_id

    def clean(self):
        super().clean()

        if not self.major_id:
            return

        if not self.program_id:
            raise ValidationError({
                "major": "A program must be selected before selecting a major."
            })

        if self.major.program_id != self.program_id:
            raise ValidationError({
                "major": "The selected major does not belong to the selected program."
            })


class StaffProfile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='staff_profile'
    )

    staff_id = models.CharField(
        max_length=7,
        unique=True
    )

    staff_type = models.CharField(
        max_length=20,
        choices=StaffType.choices
    )

    campus = models.ForeignKey(
        Campus,
        on_delete=models.PROTECT,
        related_name='staff'
    )

    def __str__(self):
        return self.staff_id


class SellerProfile(models.Model):
    """Marks a user as a seller and holds seller-only attributes.

    Every user is implicitly a buyer, so there's no buyer flag/table —
    a row here is what turns an account into a seller (checked via
    User.is_seller / user.seller_profile).
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='seller_profile'
    )

    is_verified = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f'Seller: {self.user.email}'


class OTPPurpose(models.TextChoices):
    EMAIL_VERIFICATION = 'EMAIL_VERIFICATION', 'Email Verification'
    PASSWORD_RESET = 'PASSWORD_RESET', 'Password Reset'


class EmailOTP(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='email_otps'
    )

    otp_hash = models.CharField(
        max_length=128
    )

    purpose = models.CharField(
        max_length=32,
        choices=OTPPurpose.choices,
        default=OTPPurpose.EMAIL_VERIFICATION
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    expires_at = models.DateTimeField()

    attempts = models.PositiveIntegerField(
        default=0
    )

    is_used = models.BooleanField(
        default=False
    )

    def __str__(self):
        return f'{self.get_purpose_display()} OTP for {self.user.email}'