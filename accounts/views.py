from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import SignUpForm, WorkerProfileForm, EmployerProfileForm
from .models import WorkerProfile, EmployerProfile


def signup(request):
    """User registration with role selection."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
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
    if request.user.role == 'worker':
        return redirect('job_list')
    elif request.user.role == 'employer':
        return redirect('employer_jobs')
    else:
        return redirect('admin_dashboard')


@login_required
def worker_profile(request):
    """Worker profile view and edit."""
    if request.user.role != 'worker':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    try:
        profile = request.user.worker_profile
    except WorkerProfile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        form = WorkerProfileForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            messages.success(request, 'Profile updated!')
            return redirect('job_list')
    else:
        form = WorkerProfileForm(instance=profile)

    return render(request, 'accounts/worker_profile.html', {'form': form})


@login_required
def employer_profile(request):
    """Employer profile view and edit."""
    if request.user.role != 'employer':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    try:
        profile = request.user.employer_profile
    except EmployerProfile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        form = EmployerProfileForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            messages.success(request, 'Profile updated!')
            return redirect('employer_jobs')
    else:
        form = EmployerProfileForm(instance=profile)

    return render(request, 'accounts/employer_profile.html', {'form': form})


@login_required
def admin_dashboard(request):
    """Admin dashboard for employer verification."""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    employers = EmployerProfile.objects.select_related('user').all()
    return render(request, 'accounts/admin_dashboard.html', {'employers': employers})


@login_required
def toggle_verification(request, employer_id):
    """Toggle employer verification status."""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    try:
        profile = EmployerProfile.objects.get(id=employer_id)
        profile.verified = not profile.verified
        profile.save()
        status = 'verified' if profile.verified else 'unverified'
        messages.success(request, f'{profile.company_name} is now {status}.')
    except EmployerProfile.DoesNotExist:
        messages.error(request, 'Employer not found.')

    return redirect('admin_dashboard')
