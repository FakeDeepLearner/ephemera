import uuid


from typing import cast

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from users.models import User
from utils import ApiError

from ..models import EmailMessageRecipient
from ..serializers import PasswordInputSerializer

from ..helpers import get_message_recipient, render_message_content, \
    render_message_with_password



@api_view(['GET'])
@permission_classes([AllowAny])
def email_message_view(
    request: Request,
    recipient_id: uuid.UUID) -> Response | HttpResponse:
    user = cast(User, request.user)
    # Any exception raised by get_message_recipient will be handled by the
    # global exception handler and returned as a JSON response with the appropriate status code.
    recipient: EmailMessageRecipient = get_message_recipient(recipient_id, user)

    # If the message is not password protected, we can render
    # the message content server-side in a simple HTML page
    if not recipient.is_password_protected:
        return render_message_content(request, recipient)

    # Otherwise, we return a 401 Unauthorized response to
    # indicate that a password is required to view the message.
    raise ApiError(
        message='This message is password protected. Please provide the password to view it.',
        status_code=status.HTTP_401_UNAUTHORIZED
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

    # Like the function above, any exception raised by get_message_recipient will be handled by the
    # global exception handler and returned as a JSON response with the appropriate status code.
    recipient: EmailMessageRecipient = get_message_recipient(recipient_id, user)
    return render_message_with_password(request, recipient, password)