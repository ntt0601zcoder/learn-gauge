from django.db import models

from learngaugeapis.const.clo_types import CLOType
from learngaugeapis.const.exam_formats import ExamFormat
from learngaugeapis.models.course_class import Class

class Exam(models.Model):
    id = models.AutoField(primary_key=True)
    class_id = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='exams')
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, default=None)
    clo_type = models.CharField(max_length=255, choices=CLOType.all())
    exam_format = models.CharField(max_length=255, choices=ExamFormat.all())
    chapters = models.JSONField(default=list) # Example: [1, 2, 3]
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'exams'