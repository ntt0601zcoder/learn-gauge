from django.db import models
from django.core.validators import MinValueValidator

from learngaugeapis.models.course import Course

class Class(models.Model):
    id = models.AutoField(primary_key=True)
    course_id = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='classes')
    code = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    semester = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    year = models.IntegerField(default=2025, validators=[MinValueValidator(2000)])
    description = models.TextField(null=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, default=None)

    class Meta:
        db_table = 'classes'