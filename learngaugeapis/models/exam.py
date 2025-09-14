from django.db import models

from learngaugeapis.const.exam_formats import ExamFormat
from learngaugeapis.models.course_class import Class
from learngaugeapis.models.clo_type import CLOType
from django.core.validators import MinValueValidator, MaxValueValidator

class Exam(models.Model):
    id = models.AutoField(primary_key=True)
    course_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='exams')
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, default=None)
    clo_type = models.ForeignKey(CLOType, on_delete=models.CASCADE, related_name='exams')
    exam_format = models.CharField(max_length=255, choices=ExamFormat.all())
    chapters = models.JSONField(default=list) # Example: [1, 2, 3]
    pass_expectation_rate = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    clo_pass_threshold = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, default=None)

    class Meta:
        db_table = 'exams'