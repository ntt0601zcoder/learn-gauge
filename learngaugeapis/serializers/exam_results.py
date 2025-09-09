from rest_framework import serializers
import os

from learngaugeapis.serializers.exam import CreateExamSerializer


def validate_file_extension(file):
    ext = os.path.splitext(file.name)[1].lower()
    valid_extensions = ['.xlsx', '.csv']
    if ext not in valid_extensions:
        raise serializers.ValidationError("Chỉ cho phép file .xlsx hoặc .csv.")

class UploadExamResultSerializer(CreateExamSerializer):
    answer_file = serializers.FileField(validators=[validate_file_extension])
    classification_file = serializers.FileField(validators=[validate_file_extension])
    student_answer_file = serializers.FileField(validators=[validate_file_extension])