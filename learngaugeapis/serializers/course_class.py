from rest_framework import serializers

from learngaugeapis.models.course import Course
from learngaugeapis.models.course_class import Class

class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = '__all__'
        
        
class CreateClassSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)
    name = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    location = serializers.CharField(required=True)
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.filter(deleted_at=None), 
        required=True
    )

class UpdateClassSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.filter(deleted_at=None), 
        required=False
    )