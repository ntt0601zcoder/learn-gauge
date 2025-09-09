from rest_framework import serializers

from learngaugeapis.models.course import Course
from learngaugeapis.models.course_class import Class
from learngaugeapis.models.user import User, UserRole, UserStatus

class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = '__all__'
        
        
class CreateClassSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)
    name = serializers.CharField(required=True)
    semester = serializers.IntegerField(required=True)
    year = serializers.IntegerField(required=True)
    description = serializers.CharField(required=True)
    course = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.filter(deleted_at=None), 
        required=True
    )
    teacher = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(status=UserStatus.ACTIVATED, role=UserRole.TEACHER), 
        required=False
    )

class UpdateClassSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    semester = serializers.IntegerField(required=False)
    year = serializers.IntegerField(required=False)
    description = serializers.CharField(required=False)
    course = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.filter(deleted_at=None), 
        required=False
    )
    teacher = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(status=UserStatus.ACTIVATED, role=UserRole.TEACHER), 
        required=False
    )