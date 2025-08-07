from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.base_user import BaseUserManager

class UserStatus(models.TextChoices):
    BLOCKED = "blocked"
    ACTIVATED = "activated"
    UNVERIFIED = "unverified"

class UserRole(models.TextChoices):
    ROOT = "root"
    TEACHER = "teacher"
    STUDENT = "student"

class UserGender(models.TextChoices):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class User(AbstractBaseUser):
    class Meta:
        app_label = "learngaugeapis"
        db_table = "users"

    id = models.AutoField(primary_key=True)
    card_id = models.CharField(max_length=255, unique=True, null=True)
    fullname = models.CharField(max_length=255, default="")
    birth_date = models.DateField(null=True)
    gender = models.CharField(max_length=20, choices=UserGender.choices, default=UserGender.OTHER)
    email = models.EmailField(unique=True, null=False)
    phone = models.CharField(max_length=15)
    status = models.CharField(max_length=20, choices=UserStatus.choices)
    role = models.CharField(max_length=20, choices=UserRole.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = "email"

    objects = BaseUserManager()