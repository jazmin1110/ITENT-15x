"""Validation helpers for application contract PDF uploads."""

from django.core.exceptions import ValidationError

CONTRACT_PDF_MAX_BYTES = 5 * 1024 * 1024


def validate_contract_pdf(upload) -> None:
    """Raise ValidationError if upload is not an acceptable contract PDF."""
    if not upload:
        raise ValidationError('Kailangan ang PDF file.')
    if upload.size > CONTRACT_PDF_MAX_BYTES:
        raise ValidationError('Masyadong malaki ang PDF (max 5MB).')
    name = getattr(upload, 'name', '') or ''
    if not name.lower().endswith('.pdf'):
        raise ValidationError('PDF lamang ang tinatanggap.')
