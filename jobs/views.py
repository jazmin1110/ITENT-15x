from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import (
    Avg,
    Case,
    Count,
    FloatField,
    IntegerField,
    OuterRef,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.utils import timezone
from .models import Job, Application, Rating
from .forms import JobForm, RatingForm
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
    has_active_application = False
    has_completed_application = False

    if request.user.role == 'worker':
        worker_apps = Application.objects.filter(job=job, worker=request.user)
        has_active_application = worker_apps.exclude(status='completed').exists()
        has_completed_application = worker_apps.filter(status='completed').exists()

    return render(request, 'jobs/job_detail.html', {
        'job': job,
        'has_active_application': has_active_application,
        'has_completed_application': has_completed_application,
    })


@login_required
def apply_job(request, job_id):
    """Apply for a job. Workers can reapply after a completed application."""
    if request.user.role != 'worker':
        messages.error(request, 'Only workers can apply for jobs.')
        return redirect('job_list')

    job = get_object_or_404(Job, id=job_id)

    active_application = Application.objects.filter(
        job=job, worker=request.user
    ).exclude(status='completed').exists()

    if active_application:
        messages.info(request, 'May active application ka na para sa job na ito.')
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
    sort = request.GET.get('sort', 'recommended')
    if sort not in ('recommended', 'newest', 'rating'):
        sort = 'recommended'

    worker_avg_sub = Subquery(
        Rating.objects.filter(ratee_id=OuterRef('worker_id'))
        .values('ratee')
        .annotate(a=Avg('score'))
        .values('a')[:1],
        output_field=FloatField(),
    )
    status_priority = Case(
        When(status='hired', then=Value(5)),
        When(status='shortlisted', then=Value(4)),
        When(status='viewed', then=Value(3)),
        When(status='sent', then=Value(2)),
        When(status='completed', then=Value(1)),
        default=Value(0),
        output_field=IntegerField(),
    )
    is_worker_verified = Case(
        When(
            worker__worker_profile__verification_status='verified',
            then=Value(1),
        ),
        default=Value(0),
        output_field=IntegerField(),
    )
    city_match = Case(
        When(worker__worker_profile__city__iexact=job.city, then=Value(1)),
        default=Value(0),
        output_field=IntegerField(),
    )

    annotated = (
        job.applications.select_related('worker__worker_profile', 'contract')
        .prefetch_related('ratings')
        .annotate(
            sort_status_priority=status_priority,
            sort_is_verified=is_worker_verified,
            sort_worker_avg=Coalesce(worker_avg_sub, Value(0.0)),
            sort_worker_rating_count=Count('worker__ratings_received', distinct=True),
            sort_city_match=city_match,
        )
    )

    if sort == 'newest':
        applications = list(annotated.order_by('-created_at'))
    elif sort == 'rating':
        applications = list(
            annotated.order_by(
                '-sort_worker_avg',
                '-sort_worker_rating_count',
                '-created_at',
            )
        )
    else:
        applications = list(annotated)

    job_skills = set(job.required_skills or [])
    for app in applications:
        app.employer_has_rated = any(
            r.rater_id == request.user.id for r in app.ratings.all()
        )
        skills = (
            app.worker.worker_profile.skills if app.worker.worker_profile else None
        )
        app.sort_skills_overlap = len(job_skills & set(skills or []))

    if sort == 'recommended':
        applications.sort(
            key=lambda a: (
                -a.sort_status_priority,
                -a.sort_is_verified,
                -float(a.sort_worker_avg),
                -a.sort_worker_rating_count,
                -a.sort_city_match,
                -a.sort_skills_overlap,
                -a.created_at.timestamp(),
            )
        )

    convo_map = {
        (c.job_id, c.worker_id): c
        for c in Conversation.objects.filter(job=job, employer=request.user)
    }
    for app in applications:
        app.chat_thread = convo_map.get((app.job_id, app.worker_id))

    return render(
        request,
        'jobs/applicants.html',
        {'job': job, 'applications': applications, 'sort': sort},
    )


@login_required
def update_application_status(request, application_id, status):
    """Update application status (viewed, shortlisted, hired, completed)."""
    application = get_object_or_404(
        Application.objects.select_related('job', 'contract'),
        id=application_id,
    )

    if application.job.employer != request.user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    if status not in ['viewed', 'shortlisted', 'hired', 'completed']:
        messages.error(request, 'Invalid status.')
        return redirect('applicants', job_id=application.job.id)

    if status == 'hired' and not application.hire_allowed_by_contract:
        messages.error(
            request,
            'Kumpletuhin muna ang kontrata (upload → tugon ng worker → kumpirma) bago mag-hire.',
        )
        return redirect('applicants', job_id=application.job.id)

    if status == 'hired' and application.hired_at is None:
        application.hired_at = timezone.now()
    application.status = status
    application.save()

    if status in ['shortlisted', 'hired']:
        Conversation.objects.get_or_create(
            job=application.job,
            worker=application.worker,
            employer=request.user
        )

    if status == 'completed':
        messages.success(request, 'Job marked as completed! You can now rate the worker.')
        return redirect('rate_worker', application_id=application.id)

    messages.success(request, f'Application marked as {status}.')
    return redirect('applicants', job_id=application.job.id)


@login_required
def worker_applications(request):
    """View worker's own applications."""
    if request.user.role != 'worker':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    applications = list(
        Application.objects.filter(worker=request.user)
        .select_related('job__employer__employer_profile', 'contract')
        .prefetch_related('ratings')
    )
    convo_map = {
        c.job_id: c
        for c in Conversation.objects.filter(
            worker=request.user,
            job_id__in=[a.job_id for a in applications],
        )
    }
    for app in applications:
        app.worker_has_rated = app.ratings.filter(rater=request.user).exists()
        app.chat_thread = convo_map.get(app.job_id)

    return render(request, 'jobs/worker_applications.html', {'applications': applications})


@login_required
def toggle_job_status(request, job_id):
    """Toggle job open/closed status."""
    job = get_object_or_404(Job, id=job_id, employer=request.user)
    job.status = 'closed' if job.status == 'open' else 'open'
    job.save()
    messages.success(request, f'Job is now {job.status}.')
    return redirect('employer_jobs')


@login_required
def rate_worker(request, application_id):
    """Employer rates a worker after job completion."""
    application = get_object_or_404(
        Application.objects.select_related('job', 'worker__worker_profile'),
        id=application_id
    )

    if application.job.employer != request.user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    if application.status not in ['hired', 'completed']:
        messages.error(request, 'You can only rate workers for hired/completed jobs.')
        return redirect('applicants', job_id=application.job.id)

    if Rating.objects.filter(application=application, rater=request.user).exists():
        messages.info(request, 'You have already rated this worker.')
        return redirect('applicants', job_id=application.job.id)

    if request.method == 'POST':
        form = RatingForm(request.POST)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.application = application
            rating.rater = request.user
            rating.ratee = application.worker
            rating.save()

            if application.status == 'hired':
                application.status = 'completed'
                application.save()

            messages.success(request, 'Rating submitted! Salamat!')
            return redirect('applicants', job_id=application.job.id)
    else:
        form = RatingForm()

    return render(request, 'jobs/rate_worker.html', {
        'form': form,
        'application': application,
        'worker': application.worker,
    })


@login_required
def rate_employer(request, application_id):
    """Worker rates an employer after job completion."""
    application = get_object_or_404(
        Application.objects.select_related('job__employer__employer_profile'),
        id=application_id
    )

    if application.worker != request.user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    if application.status not in ['hired', 'completed']:
        messages.error(request, 'You can only rate employers for completed jobs.')
        return redirect('worker_applications')

    if Rating.objects.filter(application=application, rater=request.user).exists():
        messages.info(request, 'You have already rated this employer.')
        return redirect('worker_applications')

    if request.method == 'POST':
        form = RatingForm(request.POST)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.application = application
            rating.rater = request.user
            rating.ratee = application.job.employer
            rating.save()
            messages.success(request, 'Rating submitted! Salamat!')
            return redirect('worker_applications')
    else:
        form = RatingForm()

    return render(request, 'jobs/rate_employer.html', {
        'form': form,
        'application': application,
        'employer': application.job.employer,
    })


@login_required
def view_ratings(request, user_id):
    """View all ratings for a user."""
    from accounts.models import User
    user = get_object_or_404(User, id=user_id)
    ratings = user.ratings_received.select_related('rater', 'application__job').order_by('-created_at')

    return render(request, 'jobs/view_ratings.html', {
        'rated_user': user,
        'ratings': ratings,
    })
