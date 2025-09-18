from django.db import models

from learngaugeapis.models.exam import Exam

class ExamResultQuerySet(models.QuerySet):
    def with_metrics(self):
        from django.db.models import F, Value, FloatField, ExpressionWrapper, Case, When
        from django.db.models.functions import Cast

        qs = self.select_related('exam', 'exam__clo_type').annotate(
            max_score=ExpressionWrapper(
                F('exam__max_score') * F('exam__clo_type__weight') / Value(100.0),
                output_field=FloatField()
            ),
            den=F('total_easy_questions') + F('total_medium_questions'),
            num=F('total_correct_easy_questions') + F('total_correct_medium_questions'),
        ).annotate(
            actual_score=Case(
                When(den=0, then=Value(0.0)),
                default=ExpressionWrapper(F('num') * F('max_score') / Cast(F('den'), FloatField()), output_field=FloatField()),
                output_field=FloatField()
            ),
            score_on_scale_10=Case(
                When(max_score=0, then=Value(0.0)),
                default=ExpressionWrapper(F('actual_score') / F('max_score') * Value(10.0), output_field=FloatField()),
                output_field=FloatField()
            ),
        ).annotate(
            letter_grade=Case(
                When(score_on_scale_10__gte=8.5, then=Value('A')),
                When(score_on_scale_10__gte=7.0, then=Value('B')),
                When(score_on_scale_10__gte=5.5, then=Value('C')),
                When(score_on_scale_10__gte=4.0, then=Value('D')),
                default=Value('F')
            ),
            is_passed=Case(
                When(score_on_scale_10__gte=F('exam__clo_pass_threshold'), then=Value(True)),
                default=Value(False)
            )
        )
        return qs


class ExamResult(models.Model):
    class Meta:
        db_table = 'exam_results'

    objects = ExamResultQuerySet.as_manager()

    id = models.AutoField(primary_key=True)
    student_code = models.CharField(max_length=255)
    student_name = models.CharField(max_length=255)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='exam_results')
    total_questions = models.IntegerField(default=0)
    total_easy_questions = models.IntegerField(default=0)
    total_medium_questions = models.IntegerField(default=0)
    total_hard_questions = models.IntegerField(default=0)
    total_correct_easy_questions = models.IntegerField(default=0)
    total_correct_medium_questions = models.IntegerField(default=0)
    total_correct_hard_questions = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)



