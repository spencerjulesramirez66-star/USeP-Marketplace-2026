"""Checks the admin's input before anything is saved.

One form is used for both creating and editing. When editing, pass
instance=<User> so the person's own email/phone are not flagged as duplicates.
"""

import re
from datetime import date

from django import forms

# Change "accounts" to the app label that holds your models.py.
from apps.accounts.models import Campus, Major, Program, StaffType, User, YearLevel

# Philippine mobile number, 11 digits (matches contact_num max_length=11).
# If you accept other formats later, change it here only.
CONTACT_PATTERN = re.compile(r'^09\d{9}$')
FIRST_ENROLLMENT_YEAR = 2000


class AccountForm(forms.Form):
    account_type = forms.ChoiceField(
        choices=[('student', 'Student'), ('staff', 'Staff'), ('admin', 'Admin')],
        required=False,                       # when editing, the type comes from the account itself
    )

    # Shared by both account types
    first_name = forms.CharField(max_length=100)
    middle_name = forms.CharField(max_length=100, required=False)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField(max_length=254)
    contact_num = forms.CharField(max_length=11)

    # Student only
    enrollment_year = forms.IntegerField(required=False)
    program = forms.ModelChoiceField(Program.objects.all(), required=False)
    major = forms.ModelChoiceField(Major.objects.all(), required=False)
    year_level = forms.ChoiceField(choices=YearLevel.choices, required=False)

    # Staff only
    campus = forms.ModelChoiceField(Campus.objects.all(), required=False)
    staff_type = forms.ChoiceField(choices=StaffType.choices, required=False)

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance

    # ---- field checks -----------------------------------------------------

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        clash = User.objects.filter(email__iexact=email)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        existing = clash.first()
        if existing:
            if existing.is_deleted:
                raise forms.ValidationError(
                    'This email belongs to a deleted account. Restore that account instead.'
                )
            raise forms.ValidationError('Another account already uses this email.')
        return email

    def clean_contact_num(self):
        number = self.cleaned_data['contact_num'].strip()
        if not CONTACT_PATTERN.match(number):
            raise forms.ValidationError('Use an 11-digit mobile number that starts with 09.')
        clash = User.objects.filter(contact_num=number)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise forms.ValidationError('Another account already uses this number.')
        return number

    # ---- checks that depend on the account type ---------------------------

    def _account_type(self):
        if self.instance:
            if self.instance.is_admin:
                return 'admin'
            return 'staff' if getattr(self.instance, 'staff_profile', None) else 'student'
        return self.cleaned_data.get('account_type')

    def clean(self):
        data = super().clean()
        kind = self._account_type()
        if kind not in ('student', 'staff', 'admin'):
            self.add_error('account_type', 'Choose Student, Staff or Admin.')
            return data
        data['account_type'] = kind

        if kind == 'student':
            self._clean_student(data)
        elif kind == 'staff':
            self._clean_staff(data)
        else:
            self._clean_admin(data)
        return data

    def _clean_student(self, data):
        if not self.instance:                  # the year is only used to build a new ID
            year = data.get('enrollment_year') or date.today().year
            if not FIRST_ENROLLMENT_YEAR <= year <= date.today().year:
                self.add_error('enrollment_year', f'Enter a year from {FIRST_ENROLLMENT_YEAR} to {date.today().year}.')
            data['enrollment_year'] = year

        program, major = data.get('program'), data.get('major')
        if major and not program:
            self.add_error('major', 'Choose a program before choosing a major.')
        elif major and major.program_id != program.pk:
            self.add_error('major', 'This major does not belong to the selected program.')

        for name in ('campus', 'staff_type'):
            data.pop(name, None)

    def _clean_staff(self, data):
        if not data.get('campus'):
            self.add_error('campus', 'Choose a campus.')
        if not data.get('staff_type'):
            self.add_error('staff_type', 'Choose a staff type.')

        for name in ('enrollment_year', 'program', 'major', 'year_level'):
            data.pop(name, None)

    def _clean_admin(self, data):
        # Admins have no student or staff profile, so none of those fields apply.
        for name in ('enrollment_year', 'program', 'major', 'year_level', 'campus', 'staff_type'):
            data.pop(name, None)