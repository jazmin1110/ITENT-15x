"""Application contract upload, acceptance, download."""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from accounts.permissions import is_platform_admin

from .contract_utils import validate_contract_pdf
from .models import Application, ApplicationContract

logger = logging.getLogger(__name__)


def _application_employer(application_id, user):
    app = get_object_or_404(
        Application.objects.select_related('job', 'contract'),
        id=application_id,
    )
    if app.job.employer_id != user.id:
        return None
    return app


@login_required
def contract_employer_upload(request, application_id):
    """POST: employer uploads PDF offer for shortlisted application."""
    app_early = get_object_or_404(Application, id=application_id)
    if request.method != 'POST':
        if app_early.job.employer_id != request.user.id:
            return redirect('dashboard')
        return redirect('applicants', job_id=app_early.job_id)

    app = _application_employer(application_id, request.user)
    if not app:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    contract, _ = ApplicationContract.objects.get_or_create(
        application=app,
        defaults={'contract_status': ApplicationContract.STATUS_NONE},
    )
    if not contract.can_employer_upload:
        messages.error(
            request,
            'I-shortlist muna ang aplikante bago mag-upload ng kontrata, o hintayin kung wala nang pending na response.',
        )
        return redirect('applicants', job_id=app.job_id)

    upload = request.FILES.get('employer_contract')
    try:
        validate_contract_pdf(upload)
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
        return redirect('applicants', job_id=app.job_id)

    contract.employer_contract_file = upload
    contract.contract_status = ApplicationContract.STATUS_EMPLOYER_UPLOADED
    contract.contract_sent_at = timezone.now()
    contract.save()
    logger.info(
        'contract employer_upload application_id=%s employer_id=%s',
        app.id,
        request.user.id,
    )
    messages.success(request, 'Na-upload ang kontrata. Hihintayin ang tugon ng worker.')
    return redirect('applicants', job_id=app.job_id)


@login_required
def contract_worker_accept(request, application_id):
    """POST: worker accepts terms and optionally uploads signed PDF."""
    if request.method != 'POST':
        return redirect('worker_applications')

    app = get_object_or_404(Application, id=application_id, worker=request.user)
    contract = get_object_or_404(ApplicationContract, application=app)
    if not contract.can_worker_respond:
        messages.error(request, 'Hindi ka puwedeng tumugon sa kontrata sa state na ito.')
        return redirect('worker_applications')

    if not request.POST.get('accept_terms'):
        messages.error(request, 'Kailangan mong i-check ang pagtanggap sa terms.')
        return redirect('worker_applications')

    signed = request.FILES.get('worker_signed')
    if signed:
        try:
            validate_contract_pdf(signed)
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
            return redirect('worker_applications')
        contract.worker_signed_file = signed

    contract.worker_accepted_terms = True
    contract.worker_accepted_at = timezone.now()
    contract.contract_status = ApplicationContract.STATUS_WORKER_RESPONDED
    contract.save()
    logger.info(
        'contract worker_respond application_id=%s worker_id=%s',
        app.id,
        request.user.id,
    )
    messages.success(request, 'Na-record ang iyong pagtanggap. Hihintayin ang kumpirmasyon ng employer.')
    return redirect('worker_applications')


@login_required
def contract_employer_confirm(request, application_id):
    """POST: employer marks contract complete after worker accepted."""
    app_early = get_object_or_404(Application, id=application_id)
    if request.method != 'POST':
        if app_early.job.employer_id != request.user.id:
            return redirect('dashboard')
        return redirect('applicants', job_id=app_early.job_id)

    app = _application_employer(application_id, request.user)
    if not app:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    contract = get_object_or_404(ApplicationContract, application=app)
    if not contract.can_employer_confirm:
        messages.error(request, 'Hindi pa handa ang kontrata para kumpirmahin.')
        return redirect('applicants', job_id=app.job_id)

    contract.contract_status = ApplicationContract.STATUS_COMPLETE
    contract.employer_confirmed_at = timezone.now()
    contract.save()
    logger.info(
        'contract complete application_id=%s employer_id=%s',
        app.id,
        request.user.id,
    )
    messages.success(
        request,
        'Kontrata ay kumpleto na. Maaari mo nang i-hire ang worker.',
    )
    return redirect('applicants', job_id=app.job_id)


@login_required
def contract_download(request, application_id, file_kind):
    """Serve employer or worker PDF to parties or staff."""
    app = get_object_or_404(Application, id=application_id)
    contract = get_object_or_404(ApplicationContract, application=app)

    allowed = False
    if is_platform_admin(request.user):
        allowed = True
    elif request.user.id == app.worker_id:
        allowed = True
    elif request.user.id == app.job.employer_id:
        allowed = True
    if not allowed:
        raise Http404()

    if file_kind == 'employer':
        field = contract.employer_contract_file
        filename = 'employer_contract.pdf'
    elif file_kind == 'worker':
        field = contract.worker_signed_file
        filename = 'worker_signed_contract.pdf'
    else:
        raise Http404()

    if not field:
        raise Http404()

    logger.info(
        'contract download application_id=%s file_kind=%s user_id=%s staff=%s',
        application_id,
        file_kind,
        request.user.id,
        is_platform_admin(request.user),
    )
    return FileResponse(
        field.open('rb'),
        as_attachment=True,
        filename=filename,
        content_type='application/pdf',
    )
