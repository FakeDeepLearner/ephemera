import uuid
from typing import Literal

from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models

# Create your models here.

class User(AbstractBaseUser):
    user_id = models.UUIDField(default = uuid.uuid4, editable = False, primary_key = True)
    created_at = models.DateTimeField(auto_now_add = True)
    class Meta:
        db_table = 'users'

