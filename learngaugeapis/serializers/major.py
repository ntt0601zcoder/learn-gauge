from rest_framework import serializers

from learngaugeapis.models.academic_program import AcademicProgram
from learngaugeapis.models.major import Major

class MajorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Major
        fields = '__all__'

class CreateMajorSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)
    name = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    academic_program_id = serializers.PrimaryKeyRelatedField(
        queryset=AcademicProgram.objects.filter(deleted_at=None), 
        required=True
    )

class UpdateMajorSerializer(serializers.Serializer):
    code = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    academic_program_id = serializers.PrimaryKeyRelatedField(
        queryset=AcademicProgram.objects.filter(deleted_at=None), 
        required=False
    )