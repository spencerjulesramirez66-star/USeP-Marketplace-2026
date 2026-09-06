from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class AccountManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', Roles.ADMIN)

        return self.create_user(
            email=email,
            password=password,
            **extra_fields
        )


class Roles(models.TextChoices):
    USER = 'USER', 'User'
    ADMIN = 'ADMIN', 'Admin'


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

    objects = AccountManager()

    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    is_first_login = models.BooleanField(default=True)

    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(
        max_length=100,
        blank=True
    )
    last_name = models.CharField(max_length=100)

    contact_num = models.CharField(
        max_length=11,
        unique=True
    )

    role = models.CharField(
        max_length=10,
        choices=Roles.choices,
        default=Roles.USER
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    profile_picture = models.ImageField(
        upload_to='uploads/',
        blank=True,
        null=True
    )

    date_joined = models.DateTimeField(
        auto_now_add=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class StudentProfile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile'
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
        related_name='students'
    )

    def __str__(self):
        return self.student_id


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