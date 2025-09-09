from rest_framework import serializers

from learngaugeapis.models.clo_type import CLOType

class CLOTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CLOType
        fields = '__all__'

class CreateCLOTypeSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)
    name = serializers.CharField(required=True)
    description = serializers.CharField(required=True)

class UpdateCLOTypeSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)