from rest_framework import serializers

from learngaugeapis.models.clo_type import CLOType
from learngaugeapis.models.course import Course

class CLOTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CLOType
        fields = '__all__'

class CreateCLOTypeSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)
    name = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.filter(deleted_at=None), required=True)

class UpdateCLOTypeSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.filter(deleted_at=None), required=False)