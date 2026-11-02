from datetime import timedelta

import pytest
from django.utils import timezone

from emailmessages.models import EmailMessage, EmailMessageRecipient, MessageView
from emailmessages.serializers import (
    EmailMessageCreateSerializer,
    EmailMessageRecipientCreateSerializer,
    EmailMessageRecipientSerializer,
    EmailMessageSerializer,
    MessageUsageResponse,
    MessageUsageResponseSerializer,
    PasswordInputSerializer,
    RecipientUsageStatisticsInputSerializer,
)

pytestmark = pytest.mark.django_db


@pytest.mark.django_db
def test_user_and_message_models_have_expected_defaults(db, user, message, recipient):
    assert user.email == "owner@example.com"
    assert user.user_id is not None
    assert message.message_id is not None
    assert message.revoked is False
    assert message.created_at is not None
    assert recipient.recipient_id is not None
    assert recipient.revoked is False
    assert recipient.password_hash is None


@pytest.mark.django_db
def test_message_relationships_and_delete_cascade(db, user, message, recipient):
    MessageView.objects.create(recipient=recipient)
    user.delete()
    message.refresh_from_db()
    assert message.associated_user is None
    assert EmailMessageRecipient.objects.filter(pk=recipient.pk).exists()

    message.delete()
    assert not EmailMessageRecipient.objects.filter(pk=recipient.pk).exists()
    assert not MessageView.objects.filter(recipient=recipient).exists()


@pytest.mark.django_db
def test_recipient_create_serializer_validates_required_and_email_fields():
    valid = EmailMessageRecipientCreateSerializer(
        data={"destination_email": "a@example.com", "is_password_protected": True}
    )
    assert valid.is_valid()
    assert valid.validated_data["is_password_protected"] is True

    invalid = EmailMessageRecipientCreateSerializer(
        data={"destination_email": "", "is_password_protected": None}
    )
    assert not invalid.is_valid()
    assert set(invalid.errors) == {"destination_email", "is_password_protected"}


@pytest.mark.django_db
def test_message_create_serializer_requires_nonempty_recipients():
    valid = EmailMessageCreateSerializer(
        data={
            "title": "Title",
            "content": "Content",
            "recipients": [
                {"destination_email": "a@example.com", "is_password_protected": False}
            ],
        }
    )
    assert valid.is_valid()
    assert "expires_at" not in valid.validated_data

    invalid = EmailMessageCreateSerializer(
        data={"title": "", "content": "", "recipients": []}
    )
    assert not invalid.is_valid()
    assert {"title", "content", "recipients"} <= set(invalid.errors)


@pytest.mark.django_db
def test_password_and_timespan_serializers():
    assert PasswordInputSerializer(data={"password": "pw"}).is_valid()
    assert not PasswordInputSerializer(data={"password": ""}).is_valid()

    for timespan in ("Last Hour", "Last 12 Hours", "Last 24 Hours"):
        serializer = RecipientUsageStatisticsInputSerializer(
            data={"timespan": timespan}
        )
        assert serializer.is_valid()
    assert not RecipientUsageStatisticsInputSerializer(
        data={"timespan": "Last year"}
    ).is_valid()


@pytest.mark.django_db
def test_output_serializers_expose_only_public_message_fields(db, message, recipient):
    message_data = EmailMessageSerializer(message).data
    assert set(message_data) == {"message_id", "title", "created_at", "recipients", "revoked"}
    assert message_data["recipients"][0]["destination_email"] == recipient.destination_email

    recipient_data = EmailMessageRecipientSerializer(recipient).data
    assert recipient_data["recipient_id"] == str(recipient.recipient_id)
    assert recipient_data["is_password_protected"] is False

    response = MessageUsageResponse(
        message_id=recipient.recipient_id,
        title=message.title,
        usage_count=3,
        created_at=message.created_at,
        revoked=False,
    )
    assert MessageUsageResponseSerializer(response).data["usage_count"] == 3


@pytest.mark.parametrize("expires_at", [None, timezone.now() + timedelta(hours=2)])
@pytest.mark.django_db
def test_email_message_fields_accept_future_expiry(db, user, expires_at):
    if expires_at is None:
        expires_at = timezone.now() + timedelta(hours=1)
    message = EmailMessage.objects.create(
        associated_user=user,
        title="Title",
        content="Content",
        expires_at=expires_at,
    )
    assert message.expires_at == expires_at
