from django.db import models
from django.core.validators import MinValueValidator

from learngaugeapis.models.major import Major

class Course(models.Model):
    id = models.AutoField(primary_key=True)
    major_id = models.ForeignKey(Major, on_delete=models.CASCADE, related_name='courses')
    code = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    number_of_credits = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    description = models.TextField(null=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, default=None)

    class Meta:
        db_table = 'courses'