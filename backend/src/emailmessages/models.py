import uuid

from users.models import User
from django.db import models

# Create your models here.

class EmailMessage(models.Model):
    message_id = models.UUIDField(default = uuid.uuid4, editable = False, primary_key = True)
    #Stores the actual HTML that will be displayed.
    content = models.TextField()
    max_views = models.IntegerField(default = 1)
    password_hash = models.CharField(blank= False, null = False)
    # Will only be stored temporarily until the password is first given out. Then, it will be set to null
    password_encrypted_value = models.CharField(blank= True, null = True)
    # Set the value to the current timestamp when the object is first created.
    created_at = models.DateTimeField(auto_now_add = True)

    #Will only be null at the moment the email message is created. Once the password is given out (for the first and only time), 
    # this field will be set to the current timestamp.
    password_given_out_at = models.DateTimeField(default = None, null = True, auto_now = False)
    destination_email = models.EmailField(blank = False, null = False)

    # Whenever a user is deleted, their email message should still
    # be available for its intended recipient to view.
    associated_user = models.ForeignKey(User, on_delete=models.SET_NULL,
                                        related_name='email_messages')

    class Meta:
        db_table = 'email_messages'
        indexes = [models.Index(fields = ['associated_user', 'created_at'])]





