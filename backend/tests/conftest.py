import sys

import pytest
from rest_framework.test import APIClient


def pytest_configure():
    from django.conf import settings
    from emailmessages import views

    # emailmessages.urls imports its view module as "views"; mirror that
    # source-tree import so the production URL configuration can be loaded.
    sys.modules.setdefault("views", views)
    settings.ROOT_URLCONF = "main.urls"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    from users.models import User

    return User.objects.create(email="owner@example.com", password="secret")


@pytest.fixture
def message(db, user):
    from datetime import timedelta

    from django.utils import timezone
    from emailmessages.models import EmailMessage

    return EmailMessage.objects.create(
        associated_user=user,
        title="A private message",
        content="The message body",
        expires_at=timezone.now() + timedelta(hours=1),
    )


@pytest.fixture
def recipient(db, message):
    from emailmessages.models import EmailMessageRecipient

    return EmailMessageRecipient.objects.create(
        associated_message=message,
        destination_email="recipient@example.com",
        is_password_protected=False,
    )


@pytest.fixture
def protected_recipient(db, message):
    from django.contrib.auth.hashers import make_password
    from emailmessages.models import EmailMessageRecipient

    return EmailMessageRecipient.objects.create(
        associated_message=message,
        destination_email="protected@example.com",
        is_password_protected=True,
        password_hash=make_password("correct-password"),
    )


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def unauthenticated_client(db):
    client = APIClient()
    #This triggers a logout, ensuring that nobody will be authenticated.
    client.force_authenticate(user=None)
    return client


@pytest.fixture(scope="session")
def django_db_use_migrations():
    return False
