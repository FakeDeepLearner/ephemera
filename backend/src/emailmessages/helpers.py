from __future__ import annotations

import os
import secrets
import uuid

from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import EmailMessageRecipient


def send_recipient_id_email(email: str, recipient_id: uuid.UUID) -> None:
    send_mail(
        subject='Your email message recipient ID',
        message=(
            'Your email message has been created.\n\n'
            f'Recipient ID: {recipient_id}'
        ),
        from_email=os.environ['EMAIL_HOST_USER'],
        recipient_list=[email],
        fail_silently=False,
    )


@transaction.atomic
def issue_recipient_password(email: str, recipient_id: uuid.UUID) -> str:
    recipient: EmailMessageRecipient = (
        EmailMessageRecipient.objects.get(recipient_id=recipient_id))

    #We can't issue password for recipients that already have a password or have been revoked.
    if recipient.password_hash is not None:
        raise ValueError("Password has already been issued for this recipient.")
    if recipient.revoked:
        raise ValueError("Password cannot be issued for a revoked recipient.")

    password = secrets.token_urlsafe(24)
    recipient.password_hash = make_password(password)
    recipient.password_created_at = timezone.now()
    recipient.save(update_fields=['password_hash', 'password_created_at'])

    send_mail(
        subject='Your email message password has been created',
        message=(
            'The password for your email message recipient record has been '
            f'created.\n\nPassword: {password}'
        ),
        from_email=os.environ['EMAIL_HOST_USER'],
        recipient_list=[email],
        fail_silently=False,
    )
    return password
