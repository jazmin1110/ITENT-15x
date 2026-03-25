import csv
import json
import statistics
from collections import defaultdict
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Max, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils import timezone

from chat.models import Conversation
from jobs.models import Application, Job

from .decorators import staff_member_required
from .models import EmployerProfile, WorkerProfile

User = get_user_model()

STAFF_PAGE_SIZE = 25

PLACEMENT_STATUSES = ('hired', 'completed')


def _weekly_hires_chart_data():
    """Last 12 calendar weeks (Mon–Sun), local date, one DB query + Python bucketing."""
    today = timezone.localdate()
    monday_this = today - timedelta(days=today.weekday())
    week_starts = [monday_this - timedelta(weeks=11 - i) for i in range(12)]

    start_dt = timezone.make_aware(datetime.combine(week_starts[0], time.min))
    end_dt = timezone.make_aware(datetime.combine(week_starts[-1] + timedelta(days=7), time.min))

    hired_times = Application.objects.filter(
        hired_at__isnull=False,
        status__in=PLACEMENT_STATUSES,
        hired_at__gte=start_dt,
        hired_at__lt=end_dt,
    ).values_list('hired_at', flat=True)

    counts = defaultdict(int)
    for ht in hired_times:
        d = timezone.localtime(ht).date()
        monday = d - timedelta(days=d.weekday())
        counts[monday] += 1

    labels = [ws.isoformat() for ws in week_starts]
    values = [counts.get(ws, 0) for ws in week_starts]
    return labels, values


def _paginate(request, queryset, per_page=STAFF_PAGE_SIZE):
    paginator = Paginator(queryset, per_page)
    page = request.GET.get('page', 1)
    try:
        return paginator.page(page)
    except PageNotAnInteger:
        return paginator.page(1)
    except EmptyPage:
        return paginator.page(paginator.num_pages)


@staff_member_required
def staff_home(request):
    pending_employers = EmployerProfile.objects.filter(verification_status='pending').count()
    pending_workers = WorkerProfile.objects.filter(verification_status='pending').count()
    open_jobs = Job.objects.filter(status='open').count()
    total_applications = Application.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    conversation_count = Conversation.objects.count()

    placements_count = Application.objects.filter(status__in=PLACEMENT_STATUSES).count()

    placement_rows = Application.objects.filter(
        status__in=PLACEMENT_STATUSES,
        hired_at__isnull=False,
    ).values_list('created_at', 'hired_at')
    deltas_days = []
    for created_at, hired_at in placement_rows:
        deltas_days.append((hired_at - created_at).total_seconds() / 86400)
    median_days_to_hire = round(statistics.median(deltas_days), 2) if deltas_days else None
    mean_days_to_hire = round(statistics.mean(deltas_days), 2) if deltas_days else None

    if total_applications:
        hire_rate_percent = round((placements_count / total_applications) * 100, 2)
    else:
        hire_rate_percent = None

    pipeline_sent = Application.objects.filter(status='sent').count()
    pipeline_viewed = Application.objects.filter(status='viewed').count()
    pipeline_shortlisted = Application.objects.filter(status='shortlisted').count()

    now = timezone.now()
    signups_7d = User.objects.filter(date_joined__gte=now - timedelta(days=7)).count()
    signups_30d = User.objects.filter(date_joined__gte=now - timedelta(days=30)).count()

    completed_with_rating = (
        Application.objects.filter(status='completed', ratings__isnull=False).distinct().count()
    )

    chart_labels, chart_counts = _weekly_hires_chart_data()

    recent_applications = (
        Application.objects.select_related('worker', 'job')
        .order_by('-created_at')[:8]
    )

    return render(request, 'staff/home.html', {
        'pending_employers': pending_employers,
        'pending_workers': pending_workers,
        'open_jobs': open_jobs,
        'total_applications': total_applications,
        'active_users': active_users,
        'conversation_count': conversation_count,
        'recent_applications': recent_applications,
        'placements_count': placements_count,
        'median_days_to_hire': median_days_to_hire,
        'mean_days_to_hire': mean_days_to_hire,
        'hire_rate_percent': hire_rate_percent,
        'pipeline_sent': pipeline_sent,
        'pipeline_viewed': pipeline_viewed,
        'pipeline_shortlisted': pipeline_shortlisted,
        'signups_7d': signups_7d,
        'signups_30d': signups_30d,
        'completed_with_rating': completed_with_rating,
        'hires_chart_labels_json': json.dumps(chart_labels),
        'hires_chart_counts_json': json.dumps(chart_counts),
    })


@staff_member_required
def staff_export_hires(request):
    stamp = timezone.localdate().strftime('%Y%m%d')
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="itent-hires-{stamp}.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow([
        'application_id',
        'worker_phone',
        'job_title',
        'job_city',
        'employer_phone',
        'employer_company',
        'applied_at',
        'hired_at',
        'days_to_hire',
        'status',
    ])

    qs = (
        Application.objects.filter(hired_at__isnull=False)
        .select_related('worker', 'job', 'job__employer', 'job__employer__employer_profile')
        .order_by('-hired_at')
    )
    for app in qs:
        emp = app.job.employer
        profile = getattr(emp, 'employer_profile', None)
        company = profile.company_name if profile else ''
        days = (
            round((app.hired_at - app.created_at).total_seconds() / 86400, 4)
            if app.hired_at and app.created_at
            else ''
        )
        writer.writerow([
            app.id,
            app.worker.phone_number,
            app.job.title,
            app.job.city,
            emp.phone_number,
            company,
            timezone.localtime(app.created_at).strftime('%Y-%m-%d %H:%M:%S'),
            timezone.localtime(app.hired_at).strftime('%Y-%m-%d %H:%M:%S'),
            days,
            app.get_status_display(),
        ])
    return response


@staff_member_required
def staff_jobs(request):
    qs = Job.objects.select_related('employer').order_by('-created_at')
    status = request.GET.get('status', '').strip()
    city = request.GET.get('city', '').strip()
    q = request.GET.get('q', '').strip()

    if status in ('open', 'closed'):
        qs = qs.filter(status=status)
    if city:
        qs = qs.filter(city__icontains=city)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(city__icontains=q))

    page_obj = _paginate(request, qs)
    return render(request, 'staff/jobs_list.html', {
        'page_obj': page_obj,
        'status': status,
        'city': city,
        'q': q,
    })


@staff_member_required
def staff_applications(request):
    qs = Application.objects.select_related('worker', 'job', 'job__employer').order_by('-created_at')
    status = request.GET.get('status', '').strip()
    valid_statuses = {c[0] for c in Application.STATUS_CHOICES}
    if status in valid_statuses:
        qs = qs.filter(status=status)

    page_obj = _paginate(request, qs)
    return render(request, 'staff/applications_list.html', {
        'page_obj': page_obj,
        'status': status,
        'status_choices': Application.STATUS_CHOICES,
    })


@staff_member_required
def staff_users(request):
    if request.method == 'POST':
        return _staff_toggle_user_active(request)

    qs = User.objects.order_by('-date_joined')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(phone_number__icontains=q)
            | Q(email__icontains=q)
        )

    page_obj = _paginate(request, qs)
    return render(request, 'staff/users_list.html', {
        'page_obj': page_obj,
        'q': q,
    })


def _staff_toggle_user_active(request):
    user_id = request.POST.get('user_id')
    target = get_object_or_404(User, pk=user_id)

    if target.pk == request.user.pk:
        messages.error(request, 'You cannot deactivate your own account from here.')
        return redirect('staff_users')

    new_active = request.POST.get('is_active') == '1'

    if not new_active and target.is_superuser:
        other_active = User.objects.filter(is_superuser=True, is_active=True).exclude(pk=target.pk).exists()
        if not other_active:
            messages.error(request, 'Cannot deactivate the last active superuser.')
            return redirect('staff_users')

    target.is_active = new_active
    target.save(update_fields=['is_active'])
    messages.success(
        request,
        f'User {target.phone_number} is now {"active" if new_active else "inactive"}.',
    )
    return redirect('staff_users')


@staff_member_required
def staff_conversations(request):
    qs = (
        Conversation.objects.select_related('job', 'worker', 'employer')
        .annotate(
            message_count=Count('messages'),
            last_message_at=Max('messages__created_at'),
        )
        .order_by('-last_message_at', '-created_at')
    )

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(job__title__icontains=q)
            | Q(worker__phone_number__icontains=q)
            | Q(employer__phone_number__icontains=q)
        )

    page_obj = _paginate(request, qs)
    return render(request, 'staff/conversations_list.html', {
        'page_obj': page_obj,
        'q': q,
    })


@staff_member_required
def staff_conversation_detail(request, pk):
    conversation = get_object_or_404(
        Conversation.objects.select_related('job', 'worker', 'employer'),
        pk=pk,
    )
    messages_qs = (
        conversation.messages.select_related('sender').order_by('created_at')
    )
    return render(request, 'staff/conversation_detail.html', {
        'conversation': conversation,
        'thread_messages': messages_qs,
    })
