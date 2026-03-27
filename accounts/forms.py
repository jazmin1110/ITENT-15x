import re
from datetime import date

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError

from jobs.skill_utils import (
    PREDEFINED_SKILL_CHOICES,
    PREDEFINED_SKILL_CODES,
    canonical_predefined_skill,
    normalize_skill_entries,
)

from .models import User, WorkerProfile, EmployerProfile
from itent.choices import CITY_CHOICES, GENDER_CHOICES, MARITAL_STATUS_CHOICES

WORKER_MAX_CUSTOM_SKILLS = 10
WORKER_CUSTOM_SKILL_NAME_MAX_LEN = 80


def _multi_get(data, key: str) -> list:
    """Like QueryDict.getlist — supports dict POST data in tests."""
    if hasattr(data, 'getlist'):
        return data.getlist(key)
    v = data.get(key)
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return list(v)
    return [v]

PH_PHONE_RE = re.compile(r'^(09\d{9}|\+639\d{9})$')

AVATAR_MAX_BYTES = 2 * 1024 * 1024


def validate_ph_phone_number_unique(phone: str, *, exclude_user: User | None = None) -> str:
    """Validate Philippine mobile format, normalize to 09…, enforce uniqueness."""
    phone = (phone or '').strip()
    if not phone:
        raise forms.ValidationError('Kailangan ng phone number.')
    if not PH_PHONE_RE.match(phone):
        raise forms.ValidationError(
            'Invalid na phone number. Gamitin ang 09XXXXXXXXX o +639XXXXXXXXX format.'
        )
    if phone.startswith('+63'):
        phone = '0' + phone[3:]
    qs = User.objects.filter(phone_number=phone)
    if exclude_user and exclude_user.pk:
        qs = qs.exclude(pk=exclude_user.pk)
    if qs.exists():
        raise forms.ValidationError('Ginagamit na ang phone number na ito.')
    return phone


def clean_profile_email(email: str, user: User | None) -> str:
    """Validate optional profile email; enforce uniqueness excluding current user."""
    email = (email or '').strip()
    if not email:
        return ''
    try:
        validate_email(email)
    except DjangoValidationError:
        raise forms.ValidationError('Invalid na email address. Suriin at subukan ulit.')
    qs = User.objects.filter(email=email)
    if user and user.pk:
        qs = qs.exclude(pk=user.pk)
    if qs.exists():
        raise forms.ValidationError('Ginagamit na ang email na ito.')
    return email


class SignUpForm(UserCreationForm):
    """Registration form with role selection."""
    role = forms.ChoiceField(choices=User.ROLE_CHOICES[:2])
    phone_number = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. 09171234567',
            'type': 'tel',
        }),
    )

    class Meta:
        model = User
        fields = ['phone_number', 'email', 'password1', 'password2', 'role']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = False
        self.fields['email'].widget.input_type = 'email'
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            return email
        try:
            validate_email(email)
        except DjangoValidationError:
            raise forms.ValidationError('Invalid na email address. Suriin at subukan ulit.')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Ginagamit na ang email na ito.')
        return email

    def clean_phone_number(self):
        return validate_ph_phone_number_unique(self.cleaned_data.get('phone_number', ''))

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['phone_number']
        if commit:
            user.save()
        return user


class WorkerProfileForm(forms.ModelForm):
    """Form for worker profile details (skills match job post: per-skill years + optional custom)."""
    SKILL_CHOICES = PREDEFINED_SKILL_CHOICES
    city = forms.ChoiceField(
        choices=[("", "Select a city")] + CITY_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Lungsod / Bayan',
    )
    skills = forms.MultipleChoiceField(
        choices=PREDEFINED_SKILL_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'optional@email.com',
            'autocomplete': 'email',
        }),
        label='Email',
    )
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'visually-hidden',
            'accept': 'image/jpeg,image/png,image/gif,image/webp',
        }),
        label='Profile picture',
    )

    class Meta:
        model = WorkerProfile
        fields = [
            'full_name',
            'date_of_birth', 'gender', 'marital_status', 'nationality', 'religion', 'languages_known',
            'city', 'contact_number',
            'doc_nbi_clearance', 'national_id_number',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date', 'autocomplete': 'bday'},
            ),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'marital_status': forms.Select(attrs={'class': 'form-select'}),
            'nationality': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'country-name',
            }),
            'religion': forms.TextInput(attrs={'class': 'form-control'}),
            'languages_known': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'hal. Tagalog, English',
            }),
            'contact_number': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'tel'}),
            'doc_nbi_clearance': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
            'national_id_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. XXXX-XXXX-XXXX-XXXX'}),
        }
        labels = {
            'date_of_birth': 'Petsa ng kapanganakan',
            'gender': 'Kasarian',
            'marital_status': 'Katayuang sibil',
            'nationality': 'Nasyonalidad',
            'religion': 'Relihiyon',
            'languages_known': 'Mga wikang alam',
            'doc_nbi_clearance': 'NBI Clearance',
            'national_id_number': 'Philippine National ID (PhilSys) Number',
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['date_of_birth'].required = True
        self.fields['gender'].required = True
        self.fields['gender'].choices = GENDER_CHOICES
        self.fields['marital_status'].required = False
        self.fields['marital_status'].choices = MARITAL_STATUS_CHOICES
        for code, label in self.SKILL_CHOICES:
            self.fields[f'years_{code}'] = forms.IntegerField(
                required=False,
                min_value=0,
                max_value=80,
                label=f'{label} — taon ng karanasan (opsyonal)',
                widget=forms.NumberInput(attrs={
                    'class': 'form-control form-control-sm',
                    'min': 0,
                    'placeholder': '—',
                }),
            )

        if self.is_bound:
            self.custom_skills_initial = self._custom_rows_from_data(self.data)
        else:
            self.custom_skills_initial = self._custom_rows_from_instance()

        self._apply_skill_initial_from_instance()

        if user:
            self.fields['email'].initial = user.email or ''
            if self._should_prefill_contact():
                self.fields['contact_number'].initial = user.phone_number

    def _custom_rows_from_data(self, data) -> list[dict]:
        names = _multi_get(data, 'custom_skill_name')
        years = _multi_get(data, 'custom_skill_years')
        n = max(len(names), len(years))
        rows = []
        for i in range(n):
            name = (names[i] if i < len(names) else '') or ''
            yraw = years[i] if i < len(years) else ''
            name = name.strip()
            ystr = (str(yraw).strip() if yraw is not None else '')
            if name or ystr:
                rows.append({'name': name, 'years': yraw if yraw is not None else ''})
        return rows

    def _custom_rows_from_instance(self) -> list[dict]:
        if not self.instance or not self.instance.pk or not self.instance.skills:
            return []
        rows = []
        for entry in normalize_skill_entries(self.instance.skills):
            name = entry['skill']
            if canonical_predefined_skill(name) is not None:
                continue
            y = entry['years_experience']
            rows.append({
                'name': name,
                'years': '' if y is None else y,
            })
        return rows

    def _apply_skill_initial_from_instance(self):
        if self.is_bound:
            return
        if not self.instance or not self.instance.pk or not self.instance.skills:
            return
        per_code_years: dict[str, int | None] = {}
        for entry in normalize_skill_entries(self.instance.skills):
            name = entry['skill']
            y = entry['years_experience']
            code = canonical_predefined_skill(name)
            if code is None:
                continue
            if code not in per_code_years:
                per_code_years[code] = y
            elif y is not None:
                prev = per_code_years[code]
                if prev is None or y > prev:
                    per_code_years[code] = y
        ordered = [c for c, _ in self.SKILL_CHOICES if c in per_code_years]
        self.fields['skills'].initial = ordered
        for code in ordered:
            y = per_code_years[code]
            yfield = f'years_{code}'
            if y is not None and yfield in self.fields:
                self.fields[yfield].initial = y

    @property
    def skill_rows(self):
        return [
            (code, label, self[f'years_{code}'])
            for code, label in self.SKILL_CHOICES
        ]

    @property
    def predefined_skills_selected_codes(self) -> list[str]:
        """Checkbox state for templates: always a list (never use `in` on a single string)."""
        v = self['skills'].value()
        if v is None:
            return []
        if isinstance(v, (list, tuple)):
            out: list[str] = []
            for x in v:
                if x is None or not str(x).strip():
                    continue
                s = str(x).strip()
                code = canonical_predefined_skill(s)
                if code is not None:
                    out.append(code)
                elif s in PREDEFINED_SKILL_CODES:
                    out.append(s)
            return out
        s = str(v).strip()
        code = canonical_predefined_skill(s)
        return [code] if code is not None else []

    def _should_prefill_contact(self):
        if not self.instance or not self.instance.pk:
            return True
        return not (self.instance.contact_number or '').strip()

    def clean_email(self):
        return clean_profile_email(self.cleaned_data.get('email', ''), self.user)

    def clean_contact_number(self):
        return validate_ph_phone_number_unique(
            self.cleaned_data.get('contact_number', ''),
            exclude_user=self.user,
        )

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob is None:
            return dob
        today = date.today()
        if dob > today:
            raise forms.ValidationError('Hindi puwedeng future ang petsa ng kapanganakan.')
        # Workers must be at least 18 (employment context).
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 18:
            raise forms.ValidationError('Dapat hindi bababa sa 18 taong gulang.')
        if age > 120:
            raise forms.ValidationError('Suriin ang petsa ng kapanganakan.')
        return dob

    def _coerce_custom_skill_years(self, raw) -> int | None:
        if raw is None or raw == '':
            return None
        try:
            y = int(raw)
        except (TypeError, ValueError):
            raise forms.ValidationError('Ilagay ang tamang bilang ng taon sa custom skill.')
        if y < 0 or y > 80:
            raise forms.ValidationError('Dapat 0–80 na taon ang karanasan sa bawat skill.')
        return y

    def clean(self):
        cleaned = super().clean()
        # Read checkbox values from POST so manual template markup always matches.
        post_skill_vals = [
            str(s).strip()
            for s in _multi_get(self.data, 'skills')
            if str(s).strip()
        ]
        selected = []
        seen_sel: set[str] = set()
        for s in post_skill_vals:
            if s not in PREDEFINED_SKILL_CODES:
                self.add_error('skills', 'Pumili ng wastong skill sa listahan.')
                return cleaned
            key = s.lower()
            if key in seen_sel:
                continue
            seen_sel.add(key)
            selected.append(s)
        cleaned['skills'] = selected
        predefined_lower = {c.lower() for c in PREDEFINED_SKILL_CODES}

        names = _multi_get(self.data, 'custom_skill_name')
        years = _multi_get(self.data, 'custom_skill_years')
        custom_out: list[tuple[str, int | None]] = []
        seen_custom: set[str] = set()

        for i, raw_name in enumerate(names):
            name = (raw_name or '').strip()
            y_raw = years[i] if i < len(years) else ''
            if not name:
                if y_raw not in (None, ''):
                    self.add_error(
                        'skills',
                        'May taon ng karanasan na nakalagay nang walang pangalan ng skill sa isa sa mga karagdagang row.',
                    )
                    return cleaned
                continue

            if len(name) > WORKER_CUSTOM_SKILL_NAME_MAX_LEN:
                self.add_error(
                    'skills',
                    f'Masyado ang haba ng pangalan ng skill (max {WORKER_CUSTOM_SKILL_NAME_MAX_LEN} na karakter).',
                )
                return cleaned
            key = name.lower()
            if key in predefined_lower:
                self.add_error(
                    'skills',
                    f'Ang "{name}" ay nasa listahan na — piliin ang checkbox sa itaas imbes na ilagay bilang custom skill.',
                )
                return cleaned
            if key in seen_custom:
                self.add_error('skills', f'May duplicate na custom skill: "{name}".')
                return cleaned
            seen_custom.add(key)

            try:
                y_val = self._coerce_custom_skill_years(y_raw)
            except forms.ValidationError as exc:
                self.add_error(
                    'skills',
                    exc.messages[0] if getattr(exc, 'messages', None) else str(exc),
                )
                return cleaned
            custom_out.append((name, y_val))

        if len(custom_out) > WORKER_MAX_CUSTOM_SKILLS:
            self.add_error(
                'skills',
                f'Masyadong maraming custom skill (max {WORKER_MAX_CUSTOM_SKILLS}).',
            )
            return cleaned

        if not selected and not custom_out:
            self.add_error(
                'skills',
                'Pumili ng kahit isang skill sa listahan o magdagdag ng custom skill.',
            )
            return cleaned

        payload: list[dict] = []
        year_values: list[int] = []

        for code in selected:
            y = cleaned.get(f'years_{code}')
            payload.append({'skill': code, 'years_experience': y})
            if y is not None:
                year_values.append(y)

        for name, y in custom_out:
            payload.append({'skill': name, 'years_experience': y})
            if y is not None:
                year_values.append(y)

        self._skills_payload = payload
        self._years_experience_agg = max(year_values) if year_values else 0
        return cleaned

    def clean_avatar(self):
        f = self.cleaned_data.get('avatar')
        if not f:
            return f
        if f.size > AVATAR_MAX_BYTES:
            raise forms.ValidationError('Masyadong malaki ang larawan (max 2MB).')
        return f

    def save(self, commit=True):
        instance = super().save(commit=False)
        normalized = []
        for item in self._skills_payload:
            raw_name = item['skill']
            canon = canonical_predefined_skill(raw_name)
            normalized.append({
                'skill': canon if canon is not None else raw_name,
                'years_experience': item['years_experience'],
            })
        instance.skills = normalized
        instance.years_experience = self._years_experience_agg
        if commit:
            instance.save()
        return instance


class EmployerProfileForm(forms.ModelForm):
    """Form for employer profile details."""
    city = forms.ChoiceField(
        choices=[("", "Select a city")] + CITY_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Lungsod / Bayan',
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'optional@email.com',
            'autocomplete': 'email',
        }),
        label='Email',
    )
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'visually-hidden',
            'accept': 'image/jpeg,image/png,image/gif,image/webp',
        }),
        label='Profile picture',
    )
    account_phone = forms.CharField(
        max_length=20,
        label='Phone number (para mag-sign in)',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'type': 'tel',
            'placeholder': 'e.g. 09171234567',
            'autocomplete': 'tel',
        }),
    )

    class Meta:
        model = EmployerProfile
        fields = [
            'company_name', 'city', 'contact_person', 'contact_number',
            'doc_sec_dti', 'doc_barangay_clearance', 'doc_mayors_permit',
            'doc_bir', 'doc_employer_registrations',
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'tel'}),
            'doc_sec_dti': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
            'doc_barangay_clearance': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
            'doc_mayors_permit': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
            'doc_bir': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
            'doc_employer_registrations': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
        }
        labels = {
            'doc_sec_dti': 'SEC (Corporation) o DTI (Sole Proprietor) Registration',
            'doc_barangay_clearance': 'Barangay Clearance',
            'doc_mayors_permit': "Mayor's Business Permit",
            'doc_bir': 'BIR Registration',
            'doc_employer_registrations': 'Employer Registrations (SSS, PhilHealth, Pag-IBIG)',
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['contact_number'].label = 'Company contact number'
        self.fields['contact_number'].required = True
        if user:
            self.fields['email'].initial = user.email or ''
            self.fields['account_phone'].initial = user.phone_number

    def clean_account_phone(self):
        return validate_ph_phone_number_unique(
            self.cleaned_data.get('account_phone', ''),
            exclude_user=self.user,
        )

    def clean_email(self):
        return clean_profile_email(self.cleaned_data.get('email', ''), self.user)

    def clean_avatar(self):
        f = self.cleaned_data.get('avatar')
        if not f:
            return f
        if f.size > AVATAR_MAX_BYTES:
            raise forms.ValidationError('Masyadong malaki ang larawan (max 2MB).')
        return f
