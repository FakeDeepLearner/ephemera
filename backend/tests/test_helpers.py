from datetime import timedelta
from unittest.mock import patch
import uuid

import pytest
from django.contrib.auth.hashers import check_password
from django.core import mail
from django.test import RequestFactory
from django.utils import timezone
from rest_framework.exceptions import APIException

from emailmessages.helpers import (
    get_message_recipient,
    get_view_count_for_recipient,
    issue_recipient_password,
    render_message_content,
    render_message_with_password,
    send_recipient_id_email,
)
from emailmessages.models import EmailMessage, EmailMessageRecipient, MessageView
from utils import ApiError

pytestmark = pytest.mark.django_db


@patch("emailmessages.helpers.send_mail")
@pytest.mark.django_db
def test_send_recipient_id_email_uses_configured_sender(
    send_mail, recipient, monkeypatch
):
    monkeypatch.setenv("EMAIL_HOST_USER", "sender@example.com")
    send_recipient_id_email(recipient.destination_email, recipient.recipient_id)
    send_mail.assert_called_once()
    assert send_mail.call_args.kwargs["from_email"] == "sender@example.com"
    assert str(recipient.recipient_id) in send_mail.call_args.kwargs["message"]


@patch("emailmessages.helpers.send_mail")
@pytest.mark.django_db
def test_issue_recipient_password_sets_hash_and_sends_mail(
    send_mail, recipient, monkeypatch
):
    monkeypatch.setenv("EMAIL_HOST_USER", "sender@example.com")
    with patch("emailmessages.helpers.secrets.token_urlsafe", return_value="generated"):
        password = issue_recipient_password(
            recipient.destination_email, recipient.recipient_id
        )

    recipient.refresh_from_db()
    assert password == "generated"
    assert check_password(password, recipient.password_hash)
    assert recipient.password_created_at is not None
    assert send_mail.call_count == 1
    assert "generated" in send_mail.call_args.kwargs["message"]

    with pytest.raises(ValueError, match="already been issued"):
        issue_recipient_password(recipient.destination_email, recipient.recipient_id)


@pytest.mark.django_db
def test_issue_recipient_password_rejects_revoked_and_missing_recipient(
    recipient, settings
):
    recipient.revoked = True
    recipient.save(update_fields=["revoked"])
    with pytest.raises(ValueError, match="revoked"):
        issue_recipient_password(recipient.destination_email, recipient.recipient_id)

    with pytest.raises(EmailMessageRecipient.DoesNotExist):
        issue_recipient_password(
            recipient.destination_email,
            uuid.UUID("00000000-0000-0000-0000-000000000000"),
        )


@pytest.mark.django_db
def test_get_message_recipient_enforces_owner_revocation_and_expiry(
    recipient, user, message
):
    other_user = type(user).objects.create(email="other@example.com", password="secret")
    assert get_message_recipient(recipient.recipient_id, user) == recipient

    with pytest.raises(ApiError) as error:
        get_message_recipient(recipient.recipient_id, other_user)
    assert error.value.status_code == 404

    recipient.revoked = True
    recipient.save(update_fields=["revoked"])
    with pytest.raises(ApiError) as error:
        get_message_recipient(recipient.recipient_id, user)
    assert error.value.status_code == 403

    recipient.revoked = False
    message.revoked = True
    message.save(update_fields=["revoked"])
    with pytest.raises(ApiError) as error:
        get_message_recipient(recipient.recipient_id, user)
    assert error.value.status_code == 403

    message.revoked = False
    message.expires_at = timezone.now() - timedelta(seconds=1)
    message.save(update_fields=["revoked", "expires_at"])
    with pytest.raises(ApiError) as error:
        get_message_recipient(recipient.recipient_id, user)
    assert error.value.status_code == 403


@pytest.mark.django_db
def test_render_helpers_log_views_and_set_no_cache_headers(recipient):
    request = RequestFactory().get("/")
    response = render_message_content(request, recipient)
    assert response.status_code == 200
    assert "A private message" in response.content.decode()
    assert response["Cache-Control"].startswith("max-age=0")
    assert response["Referrer-Policy"] == "no-referrer"
    assert MessageView.objects.filter(recipient=recipient).count() == 1


@pytest.mark.django_db
def test_render_message_with_password_rejects_missing_or_incorrect_password(
    protected_recipient
):
    request = RequestFactory().get("/")
    for password in ("wrong", ""):
        with pytest.raises(ApiError) as error:
            render_message_with_password(request, protected_recipient, password)
        assert error.value.status_code == 400

    response = render_message_with_password(request, protected_recipient, "correct-password")
    assert response.status_code == 200
    assert MessageView.objects.filter(recipient=protected_recipient).count() == 1


@pytest.mark.django_db
def test_get_view_count_for_recipient_respects_timespan(recipient):
    recent = MessageView.objects.create(recipient=recipient)
    recent.viewed_at = timezone.now() - timedelta(minutes=30)
    recent.save(update_fields=["viewed_at"])
    old = MessageView.objects.create(recipient=recipient)
    old.viewed_at = timezone.now() - timedelta(hours=2)
    old.save(update_fields=["viewed_at"])
    assert get_view_count_for_recipient(recipient, "Last Hour") == 1
    assert get_view_count_for_recipient(recipient, "Last 12 Hours") == 2
    assert get_view_count_for_recipient(recipient, "Last 24 Hours") == 2
