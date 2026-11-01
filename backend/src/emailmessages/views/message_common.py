import uuid


from typing import cast
from datetime import timedelta

from django.db import transaction
from django.db.models import QuerySet
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from django.utils import timezone

from users.models import User
from utils import ApiError

from ..models import EmailMessage, EmailMessageRecipient
from ..serializers import (
    EmailMessageCreateSerializer,
    EmailMessageSerializer,
    RecipientUsageStatisticsInputSerializer,
    MessageUsageResponse, MessageUsageResponseSerializer
)
from ..helpers import send_recipient_id_email, get_view_count_for_recipient


class EmailMessagePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    page_query_param = 'page_number'
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
    return Response(output_serializer.data, status = status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def email_recipient_usage_statistics(request: Request, recipient_id: uuid.UUID) -> Response:
    input_serializer = RecipientUsageStatisticsInputSerializer(data=request.query_params)
    input_serializer.is_valid(raise_exception = True)

    timespan = input_serializer.validated_data['timespan']


    user = cast(User, request.user)
    try:
        recipient: EmailMessageRecipient = (EmailMessageRecipient.objects.
        prefetch_related('associated_message').
        get(
            recipient_id=recipient_id,
            associated_message__associated_user=user,
        ))

        usage_count = get_view_count_for_recipient(recipient, timespan)
        response_model = MessageUsageResponse(
            message_id=recipient.recipient_id,
            title=recipient.associated_message.title,
            usage_count=usage_count,
            created_at=recipient.associated_message.created_at,
            revoked=recipient.revoked
        )

        output_serializer = MessageUsageResponseSerializer(response_model)

        return Response(output_serializer.data, status = status.HTTP_200_OK)
    except EmailMessageRecipient.DoesNotExist:
        raise ApiError(
            message = 'This message recipient either does not exist or does not belong to you.',
            status_code = status.HTTP_404_NOT_FOUND
        )