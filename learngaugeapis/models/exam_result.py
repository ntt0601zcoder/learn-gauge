from django.db import models

from learngaugeapis.models.exam import Exam

class ExamResult(models.Model):
    id = models.AutoField(primary_key=True)
    student_code = models.CharField(max_length=255)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='exam_results')
    version = models.CharField(max_length=10)
    total_questions = models.IntegerField(default=0)
    total_easy_questions = models.IntegerField(default=0)
    total_medium_questions = models.IntegerField(default=0)
    total_difficult_questions = models.IntegerField(default=0)
    total_hard_questions = models.IntegerField(default=0)
    total_correct_easy_questions = models.IntegerField(default=0)
    total_correct_medium_questions = models.IntegerField(default=0)
    total_correct_difficult_questions = models.IntegerField(default=0)
    total_correct_hard_questions = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)