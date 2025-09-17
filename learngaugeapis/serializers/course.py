from rest_framework import serializers

from learngaugeapis.models.course import Course
from learngaugeapis.models.major import Major

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'
        
        
class CreateCourseSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)
    name = serializers.CharField(required=True)
    number_of_credits = serializers.IntegerField(required=True, min_value=1)
    description = serializers.CharField(required=True)
    major = serializers.PrimaryKeyRelatedField(
        queryset=Major.objects.filter(deleted_at=None), 
        required=True
    )


class UpdateCourseSerializer(serializers.Serializer):
    code = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    number_of_credits = serializers.IntegerField(required=False, min_value=1)
    description = serializers.CharField(required=False)
    major = serializers.PrimaryKeyRelatedField(
        queryset=Major.objects.filter(deleted_at=None), 
        required=False
    )