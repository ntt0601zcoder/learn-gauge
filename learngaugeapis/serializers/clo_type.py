from rest_framework import serializers

from learngaugeapis.models.clo_type import CLOType
from learngaugeapis.models.course import Course
from learngaugeapis.serializers.course import CourseSerializer

class CLOTypeSerializer(serializers.ModelSerializer):
    metadata = serializers.SerializerMethodField()

    class Meta:
        model = CLOType
        fields = '__all__'

    def get_metadata(self, obj: CLOType):
        return {
            "course": CourseSerializer(obj.course).data,
        }

class CreateCLOTypeSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.filter(deleted_at=None), required=True)
    is_evaluation = serializers.IntegerField(required=True, min_value=0, max_value=1)

        
class _CreateCLOTypeSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    is_evaluation = serializers.IntegerField(required=True, min_value=0, max_value=1)

class BulkCreateCLOTypeSerializer(serializers.Serializer):
    clo_types = _CreateCLOTypeSerializer(many=True)
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.filter(deleted_at=None), required=True)

class UpdateCLOTypeSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.filter(deleted_at=None), required=False)
    is_evaluation = serializers.IntegerField(required=False, min_value=0, max_value=1)