import os

from django.core.files.base import ContentFile
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.db import transaction
from .decorators import staff_member_required
from .form_utils import first_invalid_field_name
from .forms import SignUpForm, WorkerProfileForm, EmployerProfileForm
from .models import User, WorkerProfile, EmployerProfile
from .permissions import is_platform_admin


class CustomLoginView(LoginView):
    """Login view that honours the 'Remember me' checkbox."""
    template_name = 'accounts/login.html'

    def form_valid(self, form):
        if not self.request.POST.get('remember'):
            self.request.session.set_expiry(0)
        else:
            self.request.session.set_expiry(1209600)  # 2 weeks
        return super().form_valid(form)


def signup(request):
    """User registration with role selection."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="accounts.backends.PhoneEmailBackend")
            messages.success(request, 'Account created! Please complete your profile.')
            if user.role == 'worker':
                return redirect('worker_profile')
            else:
                return redirect('employer_profile')
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})


@login_required
def dashboard(request):
    """Redirect to appropriate dashboard based on role."""
    if is_platform_admin(request.user):
        return redirect('staff_home')
    if request.user.role == 'worker':
        return redirect('job_list')
    if request.user.role == 'employer':
        return redirect('employer_jobs')
    return redirect('staff_home')


@login_required
def worker_profile(request):
    """Worker profile view and edit with verification documents."""
    if request.user.role != 'worker':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    try:
        profile = request.user.worker_profile
    except WorkerProfile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        form = WorkerProfileForm(
            request.POST, request.FILES, instance=profile, user=request.user,
        )
        if form.is_valid():
            new_phone = form.cleaned_data['contact_number']
            phone_changed = new_phone != request.user.phone_number
            with transaction.atomic():
                profile = form.save(commit=False)
                profile.user = request.user
                if profile.verification_status == 'rejected':
                    profile.verification_status = 'not_submitted'
                    profile.rejection_reason = ''
                profile.save()
                user = User.objects.select_for_update().get(pk=request.user.pk)
                user.email = form.cleaned_data.get('email') or ''
                avatar_flag = form.cleaned_data.get('avatar')
                upload = request.FILES.get('avatar')
                if avatar_flag is False:
                    if user.avatar:
                        user.avatar.delete(save=False)
                    user.avatar = ''
                elif upload:
                    if hasattr(upload, 'seek'):
                        upload.seek(0)
                    user.avatar.save(
                        os.path.basename(upload.name or 'avatar.jpg'),
                        ContentFile(upload.read()),
                        save=False,
                    )
                if phone_changed:
                    user.phone_number = new_phone
                    user.username = new_phone
                user.save()
            if phone_changed:
                logout(request)
                messages.success(
                    request,
                    f'Na-update ang iyong phone number. Mag-sign in ulit gamit ang {new_phone} '
                    'at iyong password (pareho pa rin). Puwede mo ring gamitin ang email mo kung naka-set.',
                )
                return redirect('login')
            messages.success(request, 'Na-save ang profile!')
            request.session['profile_saved_cta'] = 'worker'
            return redirect('worker_profile')
    else:
        form = WorkerProfileForm(instance=profile, user=request.user)

    show_profile_cta = request.session.pop('profile_saved_cta', None) == 'worker'
    profile_focus_field = first_invalid_field_name(form) if form.errors else None

    return render(request, 'accounts/worker_profile.html', {
        'form': form,
        'profile': profile,
        'show_profile_cta': show_profile_cta,
        'profile_focus_field': profile_focus_field,
    })


@login_required
def employer_profile(request):
    """Employer profile view and edit with document uploads."""
    if request.user.role != 'employer':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    try:
        profile = request.user.employer_profile
    except EmployerProfile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        form = EmployerProfileForm(
            request.POST, request.FILES, instance=profile, user=request.user,
        )
        if form.is_valid():
            new_phone = form.cleaned_data['account_phone']
            phone_changed = new_phone != request.user.phone_number
            with transaction.atomic():
                profile = form.save(commit=False)
                profile.user = request.user
                if profile.verification_status == 'rejected':
                    profile.verification_status = 'not_submitted'
                    profile.rejection_reason = ''
                profile.save()
                user = User.objects.select_for_update().get(pk=request.user.pk)
                user.email = form.cleaned_data.get('email') or ''
                avatar_flag = form.cleaned_data.get('avatar')
                upload = request.FILES.get('avatar')
                if avatar_flag is False:
                    if user.avatar:
                        user.avatar.delete(save=False)
                    user.avatar = ''
                elif upload:
                    if hasattr(upload, 'seek'):
                        upload.seek(0)
                    user.avatar.save(
                        os.path.basename(upload.name or 'avatar.jpg'),
                        ContentFile(upload.read()),
                        save=False,
                    )
                if phone_changed:
                    user.phone_number = new_phone
                    user.username = new_phone
                user.save()
            if phone_changed:
                logout(request)
                messages.success(
                    request,
                    f'Na-update ang iyong phone number. Mag-sign in ulit gamit ang {new_phone} '
                    'at iyong password (pareho pa rin). Puwede mo ring gamitin ang email mo kung naka-set.',
                )
                return redirect('login')
            messages.success(request, 'Na-save ang profile!')
            request.session['profile_saved_cta'] = 'employer'
            return redirect('employer_profile')
    else:
        form = EmployerProfileForm(instance=profile, user=request.user)

    show_profile_cta = request.session.pop('profile_saved_cta', None) == 'employer'
    profile_focus_field = first_invalid_field_name(form) if form.errors else None

    return render(request, 'accounts/employer_profile.html', {
        'form': form,
        'profile': profile,
        'show_profile_cta': show_profile_cta,
        'profile_focus_field': profile_focus_field,
    })


@login_required
def submit_verification(request):
    """Employer submits documents for admin verification."""
    if request.user.role != 'employer':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    try:
        profile = request.user.employer_profile
    except EmployerProfile.DoesNotExist:
        messages.error(request, 'I-complete muna ang profile mo.')
        return redirect('employer_profile')

    if not profile.all_docs_uploaded:
        messages.error(request, 'I-upload muna ang lahat ng required documents bago mag-submit.')
        return redirect('employer_profile')

    if profile.verification_status == 'pending':
        messages.info(request, 'Naka-submit na ang documents mo. Hinihintay ang review ng admin.')
        return redirect('employer_profile')

    profile.verification_status = 'pending'
    profile.rejection_reason = ''
    profile.save()
    messages.success(request, 'Na-submit na ang documents mo para sa verification! Hinihintay ang approval ng admin.')
    return redirect('employer_profile')


@staff_member_required
def admin_dashboard(request):
    """Admin dashboard for employer verification."""
    status_filter = request.GET.get('status', 'pending')
    employers = EmployerProfile.objects.select_related('user').all()

    if status_filter and status_filter != 'all':
        employers = employers.filter(verification_status=status_filter)

    return render(request, 'accounts/admin_dashboard.html', {
        'employers': employers,
        'status_filter': status_filter,
    })


@staff_member_required
def approve_employer(request, employer_id):
    """Admin approves employer verification."""
    profile = get_object_or_404(EmployerProfile, id=employer_id)
    profile.verification_status = 'verified'
    profile.rejection_reason = ''
    profile.save()
    messages.success(request, f'{profile.company_name} is now verified!')
    return redirect('staff_verification_employers')


@staff_member_required
def reject_employer(request, employer_id):
    """Admin rejects employer verification with a reason."""
    profile = get_object_or_404(EmployerProfile, id=employer_id)
    reason = request.POST.get('reason', '').strip() if request.method == 'POST' else ''
    profile.verification_status = 'rejected'
    profile.rejection_reason = reason or 'Hindi pumasa sa verification. Subukan ulit.'
    profile.save()
    messages.success(request, f'{profile.company_name} has been rejected.')
    return redirect('staff_verification_employers')


@staff_member_required
def revoke_employer(request, employer_id):
    """Admin revokes a previously verified employer."""
    profile = get_object_or_404(EmployerProfile, id=employer_id)
    profile.verification_status = 'not_submitted'
    profile.rejection_reason = ''
    profile.save()
    messages.success(request, f'{profile.company_name} verification has been revoked.')
    return redirect('staff_verification_employers')


# ---------------------------------------------------------------------------
# Worker verification
# ---------------------------------------------------------------------------

@login_required
def verify_national_id(request):
    """
    Placeholder for PSA eVerify National ID verification.

    In production this would call the PSA eVerify API
    (via DICT/PSA's PhilSys platform) to validate the worker's
    Philippine National ID number with a liveness check.

    Reference: https://www.ateneo.edu/features/2026/01/ateneo-build-trl-achieve-key-milestone-digital-public-infrastructure-e-verify-kyc

    TODO: Replace with actual PSA eVerify API integration when access is granted.
    """
    if request.user.role != 'worker':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    try:
        profile = request.user.worker_profile
    except WorkerProfile.DoesNotExist:
        messages.error(request, 'I-complete muna ang profile mo.')
        return redirect('worker_profile')

    if not profile.national_id_number:
        messages.error(request, 'Ilagay muna ang National ID number sa profile mo.')
        return redirect('worker_profile')

    if profile.national_id_status == 'verified':
        messages.info(request, 'Na-verify na ang National ID mo.')
        return redirect('worker_profile')

    # --- PLACEHOLDER: Simulated PSA eVerify API call ---
    # In production, this would:
    # 1. Send the PhilSys number to the PSA eVerify endpoint
    # 2. Trigger a face capture / liveness check
    # 3. Receive a verification result (match / no match)
    #
    # For now, we auto-approve to simulate a successful verification.
    profile.national_id_status = 'verified'
    profile.save()
    messages.success(request,
        'National ID verified! (Placeholder — sa production, gagamitin ang PSA eVerify API.)'
    )
    return redirect('worker_profile')


@login_required
def submit_worker_verification(request):
    """Worker submits NBI clearance + verified National ID for admin review."""
    if request.user.role != 'worker':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    try:
        profile = request.user.worker_profile
    except WorkerProfile.DoesNotExist:
        messages.error(request, 'I-complete muna ang profile mo.')
        return redirect('worker_profile')

    if not profile.all_requirements_met:
        messages.error(request,
            'I-upload ang NBI Clearance at i-verify ang National ID bago mag-submit.'
        )
        return redirect('worker_profile')

    if profile.verification_status == 'pending':
        messages.info(request, 'Naka-submit na. Hinihintay ang review ng admin.')
        return redirect('worker_profile')

    profile.verification_status = 'pending'
    profile.rejection_reason = ''
    profile.save()
    messages.success(request,
        'Na-submit na ang documents mo para sa verification! Hinihintay ang approval ng admin.'
    )
    return redirect('worker_profile')


@staff_member_required
def admin_worker_dashboard(request):
    """Admin dashboard for worker verification."""
    status_filter = request.GET.get('status', 'pending')
    workers = WorkerProfile.objects.select_related('user').all()

    if status_filter and status_filter != 'all':
        workers = workers.filter(verification_status=status_filter)

    return render(request, 'accounts/admin_worker_dashboard.html', {
        'workers': workers,
        'status_filter': status_filter,
    })


@staff_member_required
def approve_worker(request, worker_id):
    """Admin approves worker verification."""
    profile = get_object_or_404(WorkerProfile, id=worker_id)
    profile.verification_status = 'verified'
    profile.rejection_reason = ''
    profile.save()
    messages.success(request, f'{profile.full_name} is now verified!')
    return redirect('staff_verification_workers')


@staff_member_required
def reject_worker(request, worker_id):
    """Admin rejects worker verification with a reason."""
    profile = get_object_or_404(WorkerProfile, id=worker_id)
    reason = request.POST.get('reason', '').strip() if request.method == 'POST' else ''
    profile.verification_status = 'rejected'
    profile.rejection_reason = reason or 'Hindi pumasa sa verification. Subukan ulit.'
    profile.save()
    messages.success(request, f'{profile.full_name} has been rejected.')
    return redirect('staff_verification_workers')


@staff_member_required
def revoke_worker(request, worker_id):
    """Admin revokes a previously verified worker."""
    profile = get_object_or_404(WorkerProfile, id=worker_id)
    profile.verification_status = 'not_submitted'
    profile.rejection_reason = ''
    profile.save()
    messages.success(request, f'{profile.full_name} verification has been revoked.')
    return redirect('staff_verification_workers')
