from datetime import timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from emailmessages.models import EmailMessage, EmailMessageRecipient
from emailmessages.views.message_common import email_message_create
from emailmessages.views.revoke_and_delete import (
    email_message_delete,
    email_message_recipient_delete,
)
from emailmessages.views.view_message import email_message_view
from utils import ApiError

pytestmark = pytest.mark.django_db


@pytest.mark.django_db
def test_authenticated_message_list_returns_only_owned_messages(
    authenticated_client, message, user
):
    other_user = type(user).objects.create(email="other@example.com", password="secret")
    EmailMessage.objects.create(
        associated_user=other_user,
        title="Other",
        content="Hidden",
        expires_at=timezone.now() + timedelta(hours=1),
    )
    response = authenticated_client.get(reverse("emailmessages:email-message-list"))
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["title"] == message.title


@pytest.mark.django_db
def test_message_list_requires_authentication(unauthenticated_client):
    response = unauthenticated_client.get(reverse("emailmessages:email-message-list"))
    assert response.status_code == status.HTTP_403_FORBIDDEN


@patch("emailmessages.views.message_common.send_recipient_id_email")
@pytest.mark.django_db
def test_authenticated_message_create_uses_default_expiry_and_sends_ids(
    send_email, authenticated_client, user
):
    response = authenticated_client.post(
        reverse("emailmessages:email-message-create"),
        {
            "title": "Created",
            "content": "Body",
            "expires_at": (timezone.now() + timedelta(hours=2)).isoformat(),
            "recipients": [
                {"destination_email": "one@example.com", "is_password_protected": False},
                {"destination_email": "two@example.com", "is_password_protected": True},
            ],
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    message = EmailMessage.objects.get(title="Created")
    assert message.associated_user == user
    assert message.expires_at > timezone.now()
    assert EmailMessageRecipient.objects.filter(associated_message=message).count() == 2
    assert send_email.call_count == 2


@pytest.mark.django_db
def test_message_create_requires_auth_and_valid_input(unauthenticated_client, authenticated_client):
    url = reverse("emailmessages:email-message-create")
    assert unauthenticated_client.post(url, {}, format="json").status_code == 403
    response = authenticated_client.post(
        url, {"title": "", "content": "", "recipients": []}, format="json"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_recipient_view_renders_for_authenticated_owner(
    authenticated_client, recipient
):
    response = authenticated_client.get(
        reverse("emailmessages:email-recipient-view", args=[recipient.recipient_id])
    )
    assert response.status_code == 200
    assert "The message body" in response.content.decode()


@pytest.mark.django_db
def test_recipient_view_rejects_protected_and_invalid_messages(
    authenticated_client, protected_recipient, recipient, message, user
):
    url = reverse(
        "emailmessages:email-recipient-view", args=[protected_recipient.recipient_id]
    )
    assert authenticated_client.get(url).status_code == 401
    invalid_url = reverse(
        "emailmessages:email-recipient-view",
        args=["00000000-0000-0000-0000-000000000000"],
    )
    assert authenticated_client.get(invalid_url).status_code == 404

    message.expires_at = timezone.now() - timedelta(seconds=1)
    message.save(update_fields=["expires_at"])
    assert authenticated_client.get(
        reverse("emailmessages:email-recipient-view", args=[recipient.recipient_id])
    ).status_code == 403


@pytest.mark.django_db
def test_recipient_view_directly_raises_expected_api_error(
    user, protected_recipient
):
    factory = APIRequestFactory()
    request = factory.get(
        reverse(
            "emailmessages:email-recipient-view",
            args=[protected_recipient.recipient_id],
        )
    )
    request.user = user
    with pytest.raises(ApiError, match="password protected"):
        email_message_view.cls().get(request, protected_recipient.recipient_id)


@pytest.mark.django_db
def test_password_view_validates_password_and_renders(
    authenticated_client, protected_recipient
):
    url = reverse(
        "emailmessages:email-message-view", args=[protected_recipient.recipient_id]
    )
    assert authenticated_client.post(url, {}, format="json").status_code == 400
    assert authenticated_client.post(
        url, {"password": "bad"}, format="json"
    ).status_code == 400
    response = authenticated_client.post(
        url, {"password": "correct-password"}, format="json"
    )
    assert response.status_code == 200
    assert "The message body" in response.content.decode()


@pytest.mark.django_db
def test_revoke_endpoints_toggle_state_and_enforce_auth(
    authenticated_client, unauthenticated_client, message, recipient
):
    recipient_url = reverse(
        "emailmessages:email-recipient-revoke", args=[recipient.recipient_id]
    )
    message_url = reverse("emailmessages:email-message-revoke", args=[message.message_id])
    assert unauthenticated_client.patch(recipient_url).status_code == 403
    assert authenticated_client.patch(recipient_url).status_code == 200
    recipient.refresh_from_db()
    assert recipient.revoked is True
    assert authenticated_client.patch(recipient_url).status_code == 200
    recipient.refresh_from_db()
    assert recipient.revoked is False

    assert authenticated_client.patch(message_url).status_code == 200
    message.refresh_from_db()
    assert message.revoked is True
    assert authenticated_client.patch(message_url).status_code == 200
    message.refresh_from_db()
    assert message.revoked is False


@pytest.mark.django_db
def test_revoke_endpoints_return_not_found_for_other_resources(
    authenticated_client, user, message, recipient
):
    other_user = type(user).objects.create(email="other@example.com", password="secret")
    other_message = EmailMessage.objects.create(
        associated_user=other_user,
        title="Other",
        content="Body",
        expires_at=timezone.now() + timedelta(hours=1),
    )
    other_recipient = EmailMessageRecipient.objects.create(
        associated_message=other_message,
        destination_email="other@example.com",
        is_password_protected=False,
    )
    assert authenticated_client.patch(
        reverse("emailmessages:email-recipient-revoke", args=[other_recipient.recipient_id])
    ).status_code == 404
    assert authenticated_client.patch(
        reverse("emailmessages:email-message-revoke", args=[other_message.message_id])
    ).status_code == 404
    assert authenticated_client.patch(
        reverse(
            "emailmessages:email-recipient-revoke",
            args=["00000000-0000-0000-0000-000000000000"],
        )
    ).status_code == 404


@pytest.mark.django_db
def test_recipient_statistics_returns_count_and_rejects_invalid_timespan(
    authenticated_client, recipient
):
    view_url = reverse(
        "emailmessages:email-recipient-view", args=[recipient.recipient_id]
    )
    authenticated_client.get(view_url)
    stats_url = reverse(
        "emailmessages:email-recipient-usage-statistics",
        args=[recipient.recipient_id],
    )
    response = authenticated_client.get(stats_url, {"timespan": "Last Hour"})
    assert response.status_code == 200
    assert response.data["message_id"] == str(recipient.recipient_id)
    assert response.data["usage_count"] == 1
    assert response.data["title"] == recipient.associated_message.title

    invalid = authenticated_client.get(stats_url, {"timespan": "Last year"})
    assert invalid.status_code == 400
    missing = authenticated_client.get(
        reverse(
            "emailmessages:email-recipient-usage-statistics",
            args=["00000000-0000-0000-0000-000000000000"],
        ),
        {"timespan": "Last Hour"},
    )
    assert missing.status_code == 404


@pytest.mark.django_db
def test_delete_views_delete_owned_resources_and_require_auth(
    api_client, user, message, recipient
):
    factory = APIRequestFactory()
    request = factory.delete("/")
    force_authenticate(request, user=user)
    response = email_message_recipient_delete(request, recipient.recipient_id)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not EmailMessageRecipient.objects.filter(pk=recipient.pk).exists()

    request = factory.delete("/")
    force_authenticate(request, user=user)
    response = email_message_delete(request, message.message_id)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not EmailMessage.objects.filter(pk=message.pk).exists()

    unauthenticated = api_client.delete(
        reverse("emailmessages:email-message-list")
    )
    assert unauthenticated.status_code in (
        status.HTTP_403_FORBIDDEN,
        status.HTTP_405_METHOD_NOT_ALLOWED,
    )


@pytest.mark.django_db
def test_delete_views_raise_for_unknown_resources(user):
    unknown = "00000000-0000-0000-0000-000000000000"
    factory = APIRequestFactory()

    message_request = factory.delete("/")
    message_request.user = user
    with pytest.raises(ApiError, match="does not exist"):
        email_message_delete.cls().delete(message_request, unknown)

    recipient_request = factory.delete("/")
    recipient_request.user = user
    with pytest.raises(ApiError, match="does not exist"):
        email_message_recipient_delete.cls().delete(recipient_request, unknown)
