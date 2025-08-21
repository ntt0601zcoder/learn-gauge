from django.db import models
from django.core.validators import MinValueValidator

from learngaugeapis.models.course import Course

class Class(models.Model):
    id = models.AutoField(primary_key=True)
    course_id = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='classes')
    code = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    max_number_of_students = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    description = models.TextField(null=True, default=None)
    start_date = models.DateField()
    schedule = models.JSONField(default=dict)
    location = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, default=None)

    class Meta:
        db_table = 'classes'