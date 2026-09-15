import uuid

from django.db import models

# Create your models here.

class User(models.Model):
    user_id = models.UUIDField(default = uuid.uuid4, editable = False, primary_key = True)
    clerk_id = models.TextField(blank = False, null = False)
    created_at = models.DateTimeField(auto_now_add = True)


    class Meta:
        db_table = 'users'
        indexes = [models.Index(fields = ['clerk_id'])]
