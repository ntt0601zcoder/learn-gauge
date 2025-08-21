from django.db import models

from learngaugeapis.models.academic_program import AcademicProgram

class Major(models.Model):
    id = models.AutoField(primary_key=True)
    academic_program_id = models.ForeignKey(AcademicProgram, on_delete=models.CASCADE, related_name='majors')
    code = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, default=None)

    class Meta:
        db_table = 'majors'