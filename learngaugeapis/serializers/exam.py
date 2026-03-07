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
from learngaugeapis.serializers.essay_exam_result import EssayExamResultSerializer
class ExamSerializer(serializers.ModelSerializer):
    exam_results = ExamResultSerializer(many=True, read_only=True)
    essay_exam_results = EssayExamResultSerializer(many=True, read_only=True)
    metadata = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = '__all__'

    def get_metadata(self, obj: Exam):
        if obj.exam_format == ExamFormat.ESSAY:
            total_students = obj.essay_exam_results.count()
            total_passed = obj.essay_exam_results.filter(
                average_score__gte=obj.clo_pass_threshold
            ).count()
        else:
            total_students = obj.exam_results.count()
            total_passed = obj.exam_results.with_metrics().filter(is_passed=True).count()

        clo_classification_fn_map = {
            ExamFormat.MCQ: self.__get_exam_result_metadata,
            ExamFormat.ESSAY: self.__get_essay_exam_result_metadata,
        }

        return {
            "course_class": ClassSerializer(obj.course_class).data,
            "course": CourseSerializer(obj.course_class.course).data,
            "major": MajorSerializer(obj.course_class.course.major).data,
            "clo_type": CLOTypeSerializer(obj.clo_type).data,
            "academic_program": AcademicProgramSerializer(obj.course_class.course.major.academic_program).data,
            "total_students": total_students,
            "total_passed": total_passed,
            "pass_rate": total_passed / total_students * 100,
            "clo_classification": clo_classification_fn_map[obj.exam_format](obj, total_students)
        }
    
    def __get_exam_result_metadata(self, obj: Exam, total_students: int):
        return {
            "A": {
                "count": obj.exam_results.with_metrics().filter(letter_grade="A").count(),
                "percentage": obj.exam_results.with_metrics().filter(letter_grade="A").count() / total_students * 100
            },
            "B": {
                "count": obj.exam_results.with_metrics().filter(letter_grade="B").count(),
                "percentage": obj.exam_results.with_metrics().filter(letter_grade="B").count() / total_students * 100
            },
            "C": {
                "count": obj.exam_results.with_metrics().filter(letter_grade="C").count(),
                "percentage": obj.exam_results.with_metrics().filter(letter_grade="C").count() / total_students * 100
            },
            "D": {
                "count": obj.exam_results.with_metrics().filter(letter_grade="D").count(),
                "percentage": obj.exam_results.with_metrics().filter(letter_grade="D").count() / total_students * 100
            },
            "F": {
                "count": obj.exam_results.with_metrics().filter(letter_grade="F").count(),
                "percentage": obj.exam_results.with_metrics().filter(letter_grade="F").count() / total_students * 100
            }
        }
        
    def __get_essay_exam_result_metadata(self, obj: Exam, total_students: int):
        essay_results = obj.essay_exam_results
        total = essay_results.count()

        if total == 0:
            return {
                "A": {"count": 0, "percentage": 0},
                "B": {"count": 0, "percentage": 0},
                "C": {"count": 0, "percentage": 0},
                "D": {"count": 0, "percentage": 0},
                "F": {"count": 0, "percentage": 0},
            }

        # Cùng ngưỡng điểm với ExamResult: A>=8.5, B>=7.0, C>=5.5, D>=4.0, F<4.0
        a_count = essay_results.filter(average_score__gte=8.5).count()
        b_count = essay_results.filter(average_score__gte=7.0, average_score__lt=8.5).count()
        c_count = essay_results.filter(average_score__gte=5.5, average_score__lt=7.0).count()
        d_count = essay_results.filter(average_score__gte=4.0, average_score__lt=5.5).count()
        f_count = essay_results.filter(average_score__lt=4.0).count()

        return {
            "A": {"count": a_count, "percentage": a_count / total * 100},
            "B": {"count": b_count, "percentage": b_count / total * 100},
            "C": {"count": c_count, "percentage": c_count / total * 100},
            "D": {"count": d_count, "percentage": d_count / total * 100},
            "F": {"count": f_count, "percentage": f_count / total * 100},
        }

class CreateExamSerializer(serializers.Serializer):
    course_class = serializers.PrimaryKeyRelatedField(queryset=Class.objects.filter(deleted_at=None))
    name = serializers.CharField()
    description = serializers.CharField()
    clo_type = serializers.PrimaryKeyRelatedField(queryset=CLOType.objects.filter(deleted_at=None))
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