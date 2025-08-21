from rest_framework import serializers

from learngaugeapis.models.academic_program import AcademicProgram

class AcademicProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicProgram
        fields = '__all__'
        
class CreateAcademicProgramSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)
    name = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    
    
class UpdateAcademicProgramSerializer(serializers.Serializer):
    code = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)