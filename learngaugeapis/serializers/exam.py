from rest_framework import serializers

from learngaugeapis.const.exam_formats import ExamFormat
from learngaugeapis.models.course_class import Class
from learngaugeapis.models.exam import Exam
from learngaugeapis.models.course import Course
from learngaugeapis.models.clo_type import CLOType
from learngaugeapis.serializers.exam_result import ExamResultSerializer
from learngaugeapis.serializers.course_class import ClassSerializer
from learngaugeapis.serializers.course import CourseSerializer
from learngaugeapis.serializers.major import MajorSerializer
from learngaugeapis.serializers.clo_type import CLOTypeSerializer
from learngaugeapis.serializers.academic_program import AcademicProgramSerializer

class ExamSerializer(serializers.ModelSerializer):
    exam_results = ExamResultSerializer(many=True, read_only=True)
    metadata = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = '__all__'

    def get_metadata(self, obj: Exam):
        return {
            "course_class": ClassSerializer(obj.course_class).data,
            "course": CourseSerializer(obj.course_class.course).data,
            "major": MajorSerializer(obj.course_class.course.major).data,
            "clo_type": CLOTypeSerializer(obj.clo_type).data,
            "academic_program": AcademicProgramSerializer(obj.course_class.course.major.academic_program).data,
        }

class CreateExamSerializer(serializers.Serializer):
    course_class = serializers.PrimaryKeyRelatedField(queryset=Class.objects.filter(deleted_at=None))
    name = serializers.CharField()
    description = serializers.CharField()
    clo_type = serializers.PrimaryKeyRelatedField(queryset=CLOType.objects.filter(deleted_at=None))
    exam_format = serializers.ChoiceField(choices=ExamFormat.all())
    chapters = serializers.ListField(child=serializers.IntegerField(min_value=1, max_value=100))
    pass_expectation_rate = serializers.IntegerField(min_value=0, max_value=100)
    clo_pass_threshold = serializers.FloatField(min_value=0, max_value=10)
    max_score = serializers.IntegerField(min_value=0)

    def validate(self, attrs):
        _attrs = super().validate(attrs)
        
        course_class : Class = attrs['course_class']
        course : Course = course_class.course
        clo_type : CLOType = attrs['clo_type']

        if clo_type.course != course:
            raise serializers.ValidationError("CLO type must be from the same course!")

        return _attrs

class UpdateExamSerializer(serializers.Serializer):
    course_class = serializers.PrimaryKeyRelatedField(queryset=Class.objects.filter(deleted_at=None), required=False)
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    clo_type = serializers.PrimaryKeyRelatedField(queryset=CLOType.objects.filter(deleted_at=None), required=False)
    exam_format = serializers.ChoiceField(choices=ExamFormat.all(), required=False)
    chapters = serializers.ListField(child=serializers.IntegerField(min_value=1, max_value=100), required=False)
    pass_expectation_rate = serializers.IntegerField(min_value=0, max_value=100, required=False)
    clo_pass_threshold = serializers.FloatField(min_value=0, max_value=10, required=False)
    max_score = serializers.IntegerField(min_value=0, required=False)