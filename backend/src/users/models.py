import uuid

from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models

# Create your models here.


class User(AbstractBaseUser):
    user_id = models.UUIDField(default = uuid.uuid4, editable = False, primary_key = True)
    email = models.EmailField(unique = True, blank = False, null = False)
    created_at = models.DateTimeField(auto_now_add = True)
    USERNAME_FIELD = 'email'
    class Meta:
        db_table = 'users'


