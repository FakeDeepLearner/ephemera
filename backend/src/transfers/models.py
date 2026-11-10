from django.db import models
import uuid
from users.models import User
# Create your models here.

class FileTransfer(models.Model):
    transfer_id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    # Set the value to the current timestamp when the object is first created.
    created_at = models.DateTimeField(auto_now_add=True)
    # Whenever a user is deleted, their file transfers should still
    # be available for its intended recipient to view.
    associated_user = models.ForeignKey(User, on_delete=models.SET_NULL,
                                        null=True,
                                        related_name='emails')
    revoked = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=False, blank=False)

    class Meta:
        db_table = 'file_transfers'
        indexes = [models.Index(fields=['associated_user', 'created_at'])]

#Files are always stored as zip archives, and they are stored per transfer rather than per recipient.
#Both of these measures help reduce storage costs.
class StoredFile(models.Model):
    file_id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    file_name = models.TextField()
    file_size = models.BigIntegerField()

    associated_transfer = models.OneToOneField(FileTransfer, on_delete=models.CASCADE,
                                               related_name="associated_file")

    class Meta:
        db_table = 'stored_files'

class FileTransferRecipient(models.Model):
    file_id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    destination_email = models.EmailField(blank=False, null=False)

    # These fields are used to store the password hash and the timestamp when the password was created.
    # The password hash is null when the recipient is first created.
    # The password will be created when the secret is viewed for the first time.
    # When the message is first reviewed by the recipient,
    # the password_created_at will be set to the current timestamp.
    # After that, the password will not be viewable/obtainable again by anyone.
    password_hash = models.CharField(null=True, default=None)
    password_created_at = models.DateTimeField(null=True, default=None)

    is_password_protected = models.BooleanField()
    associated_message = models.ForeignKey(FileTransfer, on_delete=models.CASCADE,
                                           null=True,
                                           related_name='recipients')

    revoked = models.BooleanField(default=False)

    class Meta:
        db_table = 'file_recipients'


class FileDownload(models.Model):
    download_id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    recipient = models.ForeignKey(FileTransferRecipient, on_delete=models.CASCADE,
                                  null=True,
                                  related_name='downloads')
    downloaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'file_downloads'