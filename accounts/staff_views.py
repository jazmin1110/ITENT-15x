from django.contrib.auth import get_user_model
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from chat.models import Conversation
from jobs.models import Application, Job

from .decorators import staff_member_required
from .models import EmployerProfile, WorkerProfile

User = get_user_model()

STAFF_PAGE_SIZE = 25


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
    })


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
            Q(username__icontains=q)
            | Q(email__icontains=q)
            | Q(phone_number__icontains=q)
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
        f'User {target.username} is now {"active" if new_active else "inactive"}.',
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
            | Q(worker__username__icontains=q)
            | Q(employer__username__icontains=q)
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
