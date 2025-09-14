from django.db import models

from learngaugeapis.models.course import Course

class CLOType(models.Model):
    code = models.CharField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='clo_types')
    is_evaluation = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, default=None)

    class Meta:
        db_table = 'clo_types'