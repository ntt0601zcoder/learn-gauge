from django.db import models

from learngaugeapis.models.exam import Exam
from django.core.validators import MinValueValidator, MaxValueValidator

class EssayExamResult(models.Model):
    class Meta:
        db_table = 'essay_exam_results'
        
    id = models.AutoField(primary_key=True)
    student_code = models.CharField(max_length=255)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='essay_exam_results')
    average_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)