import uuid


from typing import cast

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from users.models import User
from utils import ApiError

from ..models import EmailMessage, EmailMessageRecipient


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def email_recipient_revoke(request: Request, recipient_id: uuid.UUID) -> Response:
    user = cast(User, request.user)

    try:
        recipient: EmailMessageRecipient = (EmailMessageRecipient.objects.
        select_related('associated_message').get(
            recipient_id = recipient_id,
            associated_message__associated_user=user
        ))
        recipient.revoked = not recipient.revoked
        recipient.save()
    except EmailMessageRecipient.DoesNotExist:
        raise ApiError(
            message = 'This message recipient either does not exist or '
                      'belongs to a message that has not been created by you.',
            status_code = status.HTTP_404_NOT_FOUND
        )

    return Response({"message": "Recipient status changed successfully."}, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def email_message_revoke(request: Request, message_id: uuid.UUID) -> Response:
    user = cast(User, request.user)
    try:
        message: EmailMessage = EmailMessage.objects.get(
            message_id=message_id,
            associated_user=user,
        )
        message.revoked = not message.revoked
        message.save()
    except EmailMessage.DoesNotExist:
        raise ApiError(
            message = 'This message either does not exist or '
                      'was not created by you.',
            status_code = status.HTTP_404_NOT_FOUND
        )

    return Response({"message": "Message status changed successfully."}, status = status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def email_message_delete(request: Request, message_id: uuid.UUID) -> Response:
    user = cast(User, request.user)
    try:
        message: EmailMessage = EmailMessage.objects.get(
            message_id=message_id,
            associated_user=user,
        )
        message.delete()
    except EmailMessage.DoesNotExist:
        raise ApiError(
            message = 'This message either does not exist or '
                      'was not created by you.',
            status_code = status.HTTP_404_NOT_FOUND
        )

    return Response({"message": "Message deleted successfully."},
                    status=status.HTTP_204_NO_CONTENT)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def email_message_recipient_delete(request: Request, recipient_id: uuid.UUID) -> Response:
    user = cast(User, request.user)
    try:
        recipient: EmailMessageRecipient = EmailMessageRecipient.objects.get(
            recipient_id=recipient_id,
            associated_message__associated_user=user,
        )
        recipient.delete()
    except EmailMessageRecipient.DoesNotExist:
        raise ApiError(
            message = 'This message recipient either does not exist or '
                      'belongs to a message that has not been created by you.',
            status_code = status.HTTP_404_NOT_FOUND
        )

    return Response({"message": "Recipient deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
