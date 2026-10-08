from __future__ import annotations

import uuid

from users.models import User
from django.db import models


# Create your models here.

class EmailMessage(models.Model):
    message_id = models.UUIDField(default = uuid.uuid4, editable = False, primary_key = True)
    title = models.TextField()
    content = models.TextField()
    # Set the value to the current timestamp when the object is first created.
    created_at = models.DateTimeField(auto_now_add = True)
    # Whenever a user is deleted, their email message should still
    # be available for its intended recipient to view.
    associated_user = models.ForeignKey(User, on_delete=models.SET_NULL,
                                        null=True,
                                        related_name='emails')
    revoked = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null = False, blank = False)

    class Meta:
        db_table = 'email_messages'
        indexes = [models.Index(fields = ['associated_user', 'created_at'])]


class EmailMessageRecipient(models.Model):
    recipient_id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    destination_email = models.EmailField(blank= False, null=False)
    # The hash is null when the recipient is first created. The password will be created
    # when the secret is viewed for the first time.
    password_hash = models.CharField(null=True, default=None)
    # When the message is first reviewed by the recipient, the password_created_at will be set to the current timestamp.
    # After that, the password will not be viewable/obtainable again by anyone
    password_created_at = models.DateTimeField(null=True, default=None)

    is_password_protected = models.BooleanField()
    #Whenever an email message is deleted, all recipient records are also deleted.
    associated_message = models.ForeignKey(EmailMessage, on_delete=models.CASCADE,
                                           null=True,
                                           related_name='recipients')

    revoked = models.BooleanField(default=False)

    class Meta:
        db_table = 'email_message_recipients'



class MessageView(models.Model):
    view_id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    recipient = models.ForeignKey(EmailMessageRecipient, on_delete=models.CASCADE,
                                  null=True,
                                  related_name='views')
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'message_views'
        indexes = [models.Index(fields=['recipient', 'viewed_at'])]