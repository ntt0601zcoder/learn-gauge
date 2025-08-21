from django.db import models

class AcademicProgram(models.Model):
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, default=None)

    class Meta:
        db_table = 'academic_programs'