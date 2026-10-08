import uuid


from typing import cast
from datetime import timedelta

from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from django.utils import timezone

from users.models import User

from .models import EmailMessage, EmailMessageRecipient
from .serializers import EmailMessageCreateSerializer, EmailMessageSerializer, PasswordInputSerializer
from .helpers import send_recipient_id_email, get_message_recipient, render_message_content, \
    render_message_with_password


class EmailMessagePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def email_message_list(request: Request) -> Response:
    user = cast(User, request.user)
    messages: QuerySet[EmailMessage] = (
        EmailMessage.objects.filter(associated_user = user)
        .prefetch_related('recipients')
        .order_by('-created_at')
    )
    paginator = EmailMessagePagination()
    page = paginator.paginate_queryset(messages, request)
    serializer = EmailMessageSerializer(page, many = True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def email_message_create(request: Request) -> Response:
    user = cast(User, request.user)
    input_serializer = EmailMessageCreateSerializer(data = request.data)
    input_serializer.is_valid(raise_exception = True)

    validated_data = input_serializer.validated_data
    recipient_data = validated_data['recipients']
    recipients: list[EmailMessageRecipient]
    with transaction.atomic():
        message = EmailMessage.objects.create(
            associated_user=user,
            title=validated_data['title'],
            content=validated_data['content'],
            expires_at=validated_data['expires_at'] or timezone.now() + timedelta(hours = 24),
        )
        recipients: list[EmailMessageRecipient] = EmailMessageRecipient.objects.bulk_create([
                EmailMessageRecipient(
                    associated_message = message,
                    destination_email = recipient['destination_email'],
                    is_password_protected = recipient['is_password_protected']
                )
                for recipient in recipient_data
            ])

    for recipient in recipients:
        send_recipient_id_email(
            recipient.destination_email,
            recipient.recipient_id,
        )

    output_serializer = EmailMessageSerializer(message)
    return Response(output_serializer.data, status = 201)


@api_view(['GET'])
@permission_classes([AllowAny])
def email_message_view(
    request: Request,
    recipient_id: uuid.UUID) -> Response | HttpResponse:
    user = cast(User, request.user)
    recipient: EmailMessageRecipient
    try:
        recipient = get_message_recipient(recipient_id, user)

        #If the message is not password protected, we can render
        # the message content server-side in a simple HTML page
        if not recipient.is_password_protected:
            return render_message_content(request, recipient)
        # Otherwise, we return a 401 Unauthorized response to
        # indicate that a password is required to view the message.
        return Response(

            {'message': 'This message is password protected. '
                        'Please provide the password to view it.'},
            status=401,
        )
    except EmailMessageRecipient.DoesNotExist:
        return Response(
            {'message': 'This message either does not exist or does not belong to you.'},
            status=404,
        )
    except PermissionError:
        return Response(
            {'message': 'This message is no longer available.'},
            status=403,
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def email_message_view_with_password(
    request: Request,
    recipient_id: uuid.UUID) -> Response | HttpResponse:

    password_serializer = PasswordInputSerializer(data = request.data)
    password_serializer.is_valid(raise_exception = True)
    password = password_serializer.validated_data['password']

    user = cast(User, request.user)
    recipient: EmailMessageRecipient
    try:
        recipient = get_message_recipient(recipient_id, user)
        return render_message_with_password(request, recipient, password)
    except EmailMessageRecipient.DoesNotExist:
        return Response(
            {'message': 'This message either does not exist or does not belong to you.'},
            status = 404,
        )
    except PermissionError:
        return Response(
            {'message': 'This message is no longer available.'},
            status = 403,
        )

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def email_recipient_revoke(request: Request, recipient_id: uuid.UUID) -> Response:
    user = cast(User, request.user)

    try:
        recipient = EmailMessageRecipient.objects.select_related('associated_message').get(
            recipient_id = recipient_id,
            revoked = False,
            associated_message__associated_user=user
        )
        recipient.revoked = True
        recipient.save()
    except EmailMessageRecipient.DoesNotExist:
        return Response({"message": "This message recipient either does not exist or "
                                  "belongs to a message that has not been created by you"}, status=404)



    return Response({"message": "Recipient revoked successfully."}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def email_message_revoke(request: Request, message_id: uuid.UUID) -> Response:
    user = cast(User, request.user)
    try:
        message = EmailMessage.objects.get(
            message_id=message_id,
            associated_user=user,
            revoked = False
        )
        message.revoked = True
        message.save()
    except EmailMessage.DoesNotExist:
        return Response({"message": "This message either does not exist or "
                                  "was not created by you"}, status = 404)

    return Response({"message": "Message revoked successfully."}, status = 200)