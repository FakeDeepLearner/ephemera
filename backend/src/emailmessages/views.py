import uuid


from typing import cast

from django.db import transaction
from django.db.models import QuerySet
from django.contrib.auth.hashers import check_password
from django.http import HttpResponse
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from users.models import User
from users.decorators import clerk_auth_exempt

from .models import EmailMessage, EmailMessageRecipient
from .serializers import EmailMessageCreateSerializer, EmailMessageSerializer, PasswordInputSerializer
from .helpers import send_recipient_id_email


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
            expires_at=validated_data['expires_at'],
        )
        recipients: list[EmailMessageRecipient] = EmailMessageRecipient.objects.bulk_create([
                EmailMessageRecipient(
                    associated_message = message,
                    destination_email = recipient['destination_email']
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


@clerk_auth_exempt
@api_view(['POST'])
def email_message_view(
    request: Request,
    recipient_id: uuid.UUID) -> Response | HttpResponse:

    password_serializer = PasswordInputSerializer(data = request.data)
    if not password_serializer.is_valid():
        return Response(
            {'message': 'Invalid password input.'},
            status = 400,
        )
    password = password_serializer.validated_data['password']

    recipient: EmailMessageRecipient
    try:
        recipient = EmailMessageRecipient.objects.select_related(
            'associated_message',
        ).get(recipient_id=recipient_id)
    except EmailMessageRecipient.DoesNotExist:
        return Response(
            {'message': 'This recipient does not exist.'},
            status=404,
        )


    # Check if the recipient or the associated message is revoked
    if recipient.revoked or recipient.associated_message.revoked:
        return Response(
            {'message': 'This message has been revoked and is no longer available.'},
            status=400,
        )

    # Check if the password is correct
    if (not recipient.password_hash
        or not check_password(password, recipient.password_hash)):
        return Response(
            {'message': 'The password is incorrect or this message has not received its password yet.'},
            status=400,
        )

    # If everything is in working order, render the message content server-side in a simple HTML page
    message: EmailMessage = recipient.associated_message
    return render(
        request,
        'emailmessages/message.html',
        {'title': message.title, 'content': message.content},
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