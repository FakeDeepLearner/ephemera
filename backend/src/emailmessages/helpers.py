from __future__ import annotations

import os
import secrets
import uuid
from datetime import timedelta

from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.response import Response

from users.models import User
from utils import ApiError
from .models import EmailMessageRecipient, EmailMessage, MessageView


def send_recipient_id_email(email: str, recipient_id: uuid.UUID) -> None:
    send_mail(
        subject='Your email message recipient ID',
        message=(
            'Your email message has been created.\n\n'
            f'Recipient ID: {recipient_id}'
        ),
        from_email=os.environ['EMAIL_HOST_USER'],
        recipient_list=[email],
        fail_silently=False
    )


@transaction.atomic
def issue_recipient_password(email: str, recipient_id: uuid.UUID) -> str:
    recipient: EmailMessageRecipient = (
        EmailMessageRecipient.objects.get(recipient_id=recipient_id))

    #We can't issue password for recipients that already have a password or have been revoked.
    if recipient.password_hash is not None:
        raise ValueError("Password has already been issued for this message.")
    if recipient.revoked:
        raise ValueError("Password cannot be issued for a revoked message.")

    password = secrets.token_urlsafe(24)
    recipient.password_hash = make_password(password)
    recipient.password_created_at = timezone.now()
    recipient.save(update_fields=['password_hash', 'password_created_at'])

    send_mail(
        subject='Your email message password has been created',
        message=(
            'The password for your this message has been '
            f'created.\n\nPassword: {password}'
            f'\n\nYou can view the message at: '
        ),
        from_email=os.environ['EMAIL_HOST_USER'],
        recipient_list=[email],
        fail_silently=False,
    )
    return password

def get_message_recipient(recipient_id: uuid.UUID, user: User) -> EmailMessageRecipient:
    try:
        recipient: EmailMessageRecipient = (
            EmailMessageRecipient.objects.select_related(
                'associated_message',
            ).get(recipient_id=recipient_id,
                  associated_message__associated_user=user)
        )
    except EmailMessageRecipient.DoesNotExist:
        raise ApiError(
            message = 'This message recipient either does not exist or does not belong to you.',
            status_code = status.HTTP_404_NOT_FOUND
        )

    if recipient.revoked or recipient.associated_message.revoked:
        raise ApiError(
            message = 'This message has been revoked and is not currently available.',
            status_code = status.HTTP_403_FORBIDDEN
        )

    if recipient.associated_message.expires_at <= timezone.now():
        raise ApiError(
            message = 'This message has expired and is no longer available.',
            status_code = status.HTTP_403_FORBIDDEN
        )

    return recipient



def render_message_content(request: Request, recipient: EmailMessageRecipient) -> HttpResponse:
    message: EmailMessage = recipient.associated_message

    #Log a message review for this recipient.
    MessageView.objects.create(recipient=recipient)

    response = render(request,
                      'emailmessages/message.html',
                      {'title': message.title, 'content': message.content},
                      status = 200)
    #Very important to ensure that this information does not get cached.
    response['Cache-Control'] = 'max-age=0, no-cache, no-store, must-revalidate, private'
    response['Referrer-Policy'] = 'no-referrer'
    return response


def render_message_with_password(request: Request, recipient: EmailMessageRecipient,
                                 password: str) -> HttpResponse | Response:

    if not recipient.password_hash or not check_password(password, recipient.password_hash):
        raise ApiError(
            message = 'The password is incorrect or this message has not received its password yet.',
            status_code = status.HTTP_400_BAD_REQUEST
        )

    return render_message_content(request, recipient)

time_ranges = {
        'Last Hour': timedelta(hours=1),
        'Last 12 Hours': timedelta(hours=12),
        'Last 24 Hours': timedelta(hours=24),
}


def get_view_count_for_recipient(recipient: EmailMessageRecipient, timespan: str) -> int:
    cutoff_time = timezone.now() - time_ranges[timespan]
    return MessageView.objects.filter(recipient=recipient,
                                      viewed_at__gte=cutoff_time).count()
