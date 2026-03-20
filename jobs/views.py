from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Job, Application
from .forms import JobForm
from chat.models import Conversation


@login_required
def job_list(request):
    """List available jobs for workers."""
    jobs = Job.objects.filter(status='open').select_related('employer__employer_profile')

    city = request.GET.get('city', '')
    skill = request.GET.get('skill', '')

    if city:
        jobs = jobs.filter(city__icontains=city)
    if skill:
        jobs = jobs.filter(required_skills__contains=skill)

    context = {
        'jobs': jobs,
        'city': city,
        'skill': skill,
        'skills': ['Masonry', 'Carpentry', 'Helper', 'Painting', 'Driver'],
    }
    return render(request, 'jobs/job_list.html', context)


@login_required
def job_detail(request, job_id):
    """View job details."""
    job = get_object_or_404(Job.objects.select_related('employer__employer_profile'), id=job_id)
    has_applied = False

    if request.user.role == 'worker':
        has_applied = Application.objects.filter(job=job, worker=request.user).exists()

    return render(request, 'jobs/job_detail.html', {
        'job': job,
        'has_applied': has_applied,
    })


@login_required
def apply_job(request, job_id):
    """Apply for a job."""
    if request.user.role != 'worker':
        messages.error(request, 'Only workers can apply for jobs.')
        return redirect('job_list')

    job = get_object_or_404(Job, id=job_id)

    if Application.objects.filter(job=job, worker=request.user).exists():
        messages.info(request, 'You have already applied for this job.')
    else:
        Application.objects.create(job=job, worker=request.user)
        messages.success(request, 'Application submitted!')

    return redirect('job_detail', job_id=job_id)


@login_required
def post_job(request):
    """Create a new job post."""
    if request.user.role != 'employer':
        messages.error(request, 'Only employers can post jobs.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.employer = request.user
            job.save()
            messages.success(request, 'Job posted!')
            return redirect('employer_jobs')
    else:
        form = JobForm()

    return render(request, 'jobs/post_job.html', {'form': form})


@login_required
def employer_jobs(request):
    """List jobs posted by the employer."""
    if request.user.role != 'employer':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    jobs = Job.objects.filter(employer=request.user)
    return render(request, 'jobs/employer_jobs.html', {'jobs': jobs})


@login_required
def applicants(request, job_id):
    """View applicants for a job."""
    job = get_object_or_404(Job, id=job_id, employer=request.user)
    applications = job.applications.select_related('worker__worker_profile')
    return render(request, 'jobs/applicants.html', {'job': job, 'applications': applications})


@login_required
def update_application_status(request, application_id, status):
    """Update application status (viewed, shortlisted, hired)."""
    application = get_object_or_404(Application, id=application_id)

    if application.job.employer != request.user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    if status not in ['viewed', 'shortlisted', 'hired']:
        messages.error(request, 'Invalid status.')
        return redirect('applicants', job_id=application.job.id)

    application.status = status
    application.save()

    if status in ['shortlisted', 'hired']:
        Conversation.objects.get_or_create(
            job=application.job,
            worker=application.worker,
            employer=request.user
        )

    messages.success(request, f'Application marked as {status}.')
    return redirect('applicants', job_id=application.job.id)


@login_required
def worker_applications(request):
    """View worker's own applications."""
    if request.user.role != 'worker':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    applications = Application.objects.filter(worker=request.user).select_related('job__employer__employer_profile')
    return render(request, 'jobs/worker_applications.html', {'applications': applications})


@login_required
def toggle_job_status(request, job_id):
    """Toggle job open/closed status."""
    job = get_object_or_404(Job, id=job_id, employer=request.user)
    job.status = 'closed' if job.status == 'open' else 'open'
    job.save()
    messages.success(request, f'Job is now {job.status}.')
    return redirect('employer_jobs')
