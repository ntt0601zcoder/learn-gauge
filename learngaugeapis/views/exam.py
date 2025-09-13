import logging
from datetime import datetime
from rest_framework.viewsets import ViewSet
from rest_framework import status
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
import pandas as pd
import numpy as np
from django.db import transaction

from learngaugeapis.helpers.response import RestResponse
from learngaugeapis.helpers.paginator import CustomPageNumberPagination
from learngaugeapis.middlewares.authentication import UserAuthentication
from learngaugeapis.middlewares.permissions import IsRoot
from learngaugeapis.models.course import Course
from learngaugeapis.models.exam import Exam
from learngaugeapis.models.exam_result import ExamResult
from learngaugeapis.serializers.exam import CreateExamSerializer, ExamSerializer, UpdateExamSerializer
from learngaugeapis.serializers.exam_results import UploadExamResultSerializer
from learngaugeapis.errors.exceptions import InvalidFileContentException

class ExamView(ViewSet):
    authentication_classes = [UserAuthentication]
    paginator = CustomPageNumberPagination()

    def get_permissions(self):
        if self.action in ['create', 'update', 'destroy']:
            return [IsRoot()]
        return []
    
    @swagger_auto_schema(
        responses={200: ExamSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter(
                name="size",
                in_="query",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                name="page",
                in_="query",
                type=openapi.TYPE_INTEGER,
                required=False
            )
        ]
    )
    def list(self, request):
        try:
            logging.getLogger().info("ExamView.list params=%s", request.query_params)
            exams = Exam.objects.filter(deleted_at=None).order_by("-created_at")
            exams = self.paginator.paginate_queryset(exams, request)
            serializer = ExamSerializer(exams, many=True)
            return RestResponse(status=status.HTTP_200_OK, data=self.paginator.get_paginated_data(serializer.data)).response
        except Exception as e:
            logging.getLogger().error("ExamView.list exc=%s", str(e))
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    def retrieve(self, request, pk=None):
        try:
            logging.getLogger().info("ExamView.retrieve pk=%s", pk)
            exam = Exam.objects.get(id=pk, deleted_at=None)
            serializer = ExamSerializer(exam)
            return RestResponse(status=status.HTTP_200_OK, data=serializer.data).response
        except Exam.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND).response
        except Exception as e:
            logging.getLogger().error("ExamView.retrieve exc=%s", str(e))
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    # @swagger_auto_schema(request_body=CreateExamSerializer)
    # def create(self, request):
    #     try:
    #         logging.getLogger().info("ExamView.create req=%s", request.data)
    #         serializer = CreateExamSerializer(data=request.data)

    #         if not serializer.is_valid():
    #             return RestResponse(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors).response
            
    #         exam = Exam.objects.create(**serializer.validated_data)
    #         serializer = ExamSerializer(exam)
    #         return RestResponse(status=status.HTTP_201_CREATED, data=serializer.data).response
    #     except Exception as e:
    #         logging.getLogger().error("ExamView.create exc=%s", str(e))
    #         return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    # @swagger_auto_schema(request_body=UpdateExamSerializer)
    # def update(self, request, pk=None):
    #     try:
    #         logging.getLogger().info("ExamView.update pk=%s, req=%s", pk, request.data)
    #         exam = Exam.objects.get(id=pk, deleted_at=None)
    #         serializer = UpdateExamSerializer(exam, data=request.data)
            
    #         if not serializer.is_valid():
    #             return RestResponse(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors).response
            
    #         validated_data = serializer.validated_data

    #         for key, value in validated_data.items():
    #             setattr(exam, key, value)

    #         exam.save()
    #         serializer = ExamSerializer(exam)

    #         return RestResponse(status=status.HTTP_200_OK, data=serializer.data).response
    #     except Exam.DoesNotExist:
    #         return RestResponse(status=status.HTTP_404_NOT_FOUND).response
    #     except Exception as e:
    #         logging.getLogger().error("ExamView.update exc=%s", str(e))
    #         return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    def destroy(self, request, pk=None):
        try:
            logging.getLogger().info("ExamView.destroy pk=%s", pk)
            exam = Exam.objects.get(id=pk, deleted_at=None)
            exam.deleted_at = datetime.now()
            exam.save()
            return RestResponse(status=status.HTTP_204_NO_CONTENT).response
        except Exam.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND).response
        except Exception as e:
            logging.getLogger().error("ExamView.destroy exc=%s", str(e))
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response

    @swagger_auto_schema(request_body=UploadExamResultSerializer)
    @action(detail=False, methods=['post'], url_path='upload-exam-results', parser_classes=[MultiPartParser])
    def upload_exam_results(self, request):
        try:
            logging.getLogger().info("ExamView.upload_exam_results req=%s", request.data)
            serializer = UploadExamResultSerializer(data=request.data)

            if not serializer.is_valid():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors).response

            validated_data = serializer.validated_data

            course  = Course.objects.get(classes=validated_data['course_class'])
            answer_file = validated_data.pop('answer_file')
            classification_file = validated_data.pop('classification_file')
            student_answer_file = validated_data.pop('student_answer_file')

            answer_data = self.__load_and_validate_answer_file(course.code, answer_file)
            classification_data = self.__load_and_validate_classification_file(course.code, classification_file)
            student_answer_data = self.__load_and_validate_student_answer_file(course.code, student_answer_file)

            self.__validate_exam_result_data(course.code, answer_data, classification_data, student_answer_data)
            self.__consolidate_exam_result_data(course.code, answer_data, classification_data, student_answer_data)

            with transaction.atomic():
                exam = Exam.objects.create(
                    course_class=validated_data['course_class'],
                    name=validated_data["name"],
                    description=validated_data["description"],
                    clo_type=validated_data["clo_type"],
                    exam_format=validated_data["exam_format"],
                    chapters=validated_data["chapters"],
                )

                exam_results = []

                for student_code, student_data in student_answer_data.items():
                    print(student_data)
                    exam_results.append(
                        ExamResult(
                            student_code=student_code,
                            exam=exam,
                            total_questions=student_data["number_of_questions"],
                            total_easy_questions=student_data["number_of_easy_questions"],
                            total_medium_questions=student_data["number_of_medium_questions"],
                            total_hard_questions=student_data["number_of_correct_hard_questions"],
                            total_correct_easy_questions=student_data["number_of_correct_easy_questions"],
                            total_correct_medium_questions=student_data["number_of_correct_medium_questions"],
                            total_correct_hard_questions=student_data["number_of_correct_hard_questions"],
                        )
                    )
                
                ExamResult.objects.bulk_create(exam_results)
            return RestResponse(status=status.HTTP_200_OK, data=ExamSerializer(exam).data).response
        except Course.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND, data="Không tìm thấy học phần tương ứng!").response
        except InvalidFileContentException as e:
            return RestResponse(status=status.HTTP_400_BAD_REQUEST, message=str(e)).response
        except Exception as e:
            logging.getLogger().error("ExamView.upload_exam_results exc=%s", str(e))
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response

    def __consolidate_exam_result_data(self, course_code, answer_data, classification_data, student_answer_data):
        for _, student_data in student_answer_data.items():
            student_data["number_of_correct_easy_questions"] = 0
            student_data["number_of_correct_medium_questions"] = 0
            student_data["number_of_correct_hard_questions"] = 0
            student_data["number_of_correct_questions"] = 0
            student_data["number_of_easy_questions"] = 0
            student_data["number_of_medium_questions"] = 0
            student_data["number_of_hard_questions"] = 0

            for question_code, answer in student_data['answers'].items():
                is_correct = answer == answer_data["questions"][question_code]["correct_answer"]
                
                if is_correct:
                    student_data["number_of_correct_questions"] += 1
                    
                if answer_data["questions"][question_code]["difficulty"] == "d":
                    student_data["number_of_easy_questions"] += 1

                    if is_correct:
                        student_data["number_of_correct_easy_questions"] += 1
                elif answer_data["questions"][question_code]["difficulty"] == "t":
                    student_data["number_of_medium_questions"] += 1

                    if is_correct:
                        student_data["number_of_correct_medium_questions"] += 1
                elif answer_data["questions"][question_code]["difficulty"] == "k":
                    student_data["number_of_hard_questions"] += 1

                    if is_correct:
                        student_data["number_of_correct_hard_questions"] += 1

    def __validate_exam_result_data(self, course_code, answer_data, classification_data, student_answer_data):
        if len(answer_data["questions"]) != len(classification_data):
            raise InvalidFileContentException("Số lượng câu hỏi trong file đáp án và file câu hỏi - chương không khớp!")

        unique_student_question_codes = set()

        for _, student_data in student_answer_data.items():
            for question_code in student_data['answers'].keys():
                unique_student_question_codes.add(question_code)

        unknown_question_codes = unique_student_question_codes - set(answer_data["questions"].keys())

        if unknown_question_codes:
            raise InvalidFileContentException(f"Có các câu hỏi trong file đáp án của sinh viên không tồn tại trong file đáp án: {', '.join(unknown_question_codes)}")

        number_of_questions_per_student = {}
        for student_id, student_data in student_answer_data.items():
            number_of_questions_per_student[student_id] = len(student_data['answers'])

        if len(set(number_of_questions_per_student.values())) > 1:
            submsg = ", ".join([f"{student_id} có {number_of_questions_per_student[student_id]}" for student_id in number_of_questions_per_student.keys()])
            raise InvalidFileContentException(f"Số lượng câu hỏi trong file đáp án của sinh viên không tương đồng: {submsg}")

    
    def __load_and_validate_answer_file(self, course_code, file):
        df = pd.read_excel(file)
        df = df.map(lambda x: x.lower() if isinstance(x, str) else x)
        df.columns = df.columns.map(str.lower)
        df = df.rename(columns={'mã': 'question_code', 'đáp án đúng': 'correct_answer'})

        data = {
            "questions": {},
            "exams": {},
        }
        duplicate_question_codes = set()
        course_codes = set()
        invalid_question_codes = set()

        for _, row in df.iterrows():
            if row['question_code'] in data:
                duplicate_question_codes.add(row['question_code'])
                continue

            _course_code = row['question_code'][:-7].lower()

            if _course_code != course_code.lower():
                invalid_question_codes.add(row['question_code'][:-7].lower())

            course_codes.add(row['question_code'][:-7].lower())

            data["questions"][row['question_code']] = {
                "correct_answer": row['correct_answer'],
                "difficulty": row['question_code'][-1].lower(),
                "no": row['question_code'][-4:-1].lower(),
                "version": row['question_code'][-7:-4].lower(),
                "course_code": row['question_code'][:-7].lower(),
            }
            
            if row['question_code'][-7:-4].lower() not in data["exams"]:
                data["exams"][row['question_code'][-7:-4].lower()] = {
                    "number_of_questions": 1,
                }
            else:
                data["exams"][row['question_code'][-7:-4].lower()]["number_of_questions"] += 1

        all_exams_have_same_number_of_questions = all(data["exams"][exam]["number_of_questions"] == data["exams"][list(data["exams"].keys())[0]]["number_of_questions"] for exam in data["exams"])

        if not all_exams_have_same_number_of_questions:
            raise InvalidFileContentException(f"Các mã đề thi có số lượng câu hỏi không tương đồng!")

        if duplicate_question_codes:
            raise InvalidFileContentException(f"File đáp án có {len(duplicate_question_codes)} mã câu hỏi bị trùng lặp: {', '.join(duplicate_question_codes)}")

        if invalid_question_codes:
            raise InvalidFileContentException(f"File đáp án có các câu không thuộc môn học {course_code}: {', '.join(invalid_question_codes)}")
        
        if len(course_codes) > 1:
            raise InvalidFileContentException(f"File đáp án có các câu không thuộc cùng 1 môn học: {', '.join(course_codes)}")
        
        return data

    def __load_and_validate_classification_file(self, course_code, file):
        df = pd.read_excel(file)
        df = df.map(lambda x: x.lower() if isinstance(x, str) else x)
        df.columns = df.columns.map(str.lower)
        df = df.rename(columns={'mã đề': 'question_code', 'chương': 'chapter'})

        data = {}
        duplicate_question_codes = set()
        course_codes = set()
        invalid_question_codes = set()

        for _, row in df.iterrows():
            if row['question_code'] in data:
                duplicate_question_codes.add(row['question_code'])
                continue

            _course_code = row['question_code'][:-7].lower()

            if _course_code != course_code.lower():
                invalid_question_codes.add(row['question_code'][:-7].lower())

            course_codes.add(row['question_code'][:-7].lower())
            data[row['question_code']] = row['chapter']

        if duplicate_question_codes:
            raise InvalidFileContentException(f"File câu hỏi - chương có {len(duplicate_question_codes)} mã câu hỏi bị trùng lặp: {', '.join(duplicate_question_codes)}")

        if invalid_question_codes:
            raise InvalidFileContentException(f"File câu hỏi - chương có các câu không thuộc môn học {course_code}: {', '.join(invalid_question_codes)}")
        
        if len(course_codes) > 1:
            raise InvalidFileContentException(f"File câu hỏi - chương có các câu không thuộc cùng 1 môn học: {', '.join(course_codes)}")

        return data

    def __load_and_validate_student_answer_file(self, course_code, file):
        df = pd.read_excel(file)
        df = df.map(lambda x: x.lower() if isinstance(x, str) else x)
        df.columns = df.columns.map(str.lower)
        df = df.replace({np.nan: None})
        df = df.rename(columns={'mssv': 'student_code', 'stt': 'question_number', 'họ tên': 'student_name'})

        duplicate_question_codes = df.columns[df.columns.duplicated()].unique().tolist()

        if duplicate_question_codes:
            raise InvalidFileContentException(f"File đáp án của sinh viên có {len(duplicate_question_codes)} mã câu hỏi bị trùng lặp: {', '.join(duplicate_question_codes)}")

        data = {}
        course_codes = set()
        student_ids = set()
        invalid_question_codes = set()

        for _, row in df.iterrows():
            student_id = str(row['student_code']).strip()
            answers = row.drop(labels=['student_code', 'question_number', 'student_name']).dropna().to_dict()

            if student_id in data:
                student_ids.add(student_id)

            version = set()
            data[student_id] = {}
            data[student_id]["answers"] = answers
            data[student_id]["number_of_questions"] = len(answers)

            for question_code, answer in answers.items():
                _course_code = question_code[:-7].lower()

                if _course_code != course_code.lower():
                    invalid_question_codes.add(question_code[:-7].lower())

                course_codes.add(question_code[:-7].lower())
                version.add(question_code[-7:-4].lower())

            if len(version) > 1:
                raise InvalidFileContentException(f"File đáp án của sinh viên {student_id} có các câu không thuộc cùng 1 mã đề thi: {', '.join(version)}")

        if student_ids:
            raise InvalidFileContentException(f"Có {len(student_ids)} mã sinh viên bị trùng lặp: {student_ids.join(', ')}")

        if invalid_question_codes:
            raise InvalidFileContentException(f"File đáp án của sinh viên có các câu không thuộc môn học {course_code}: {', '.join(invalid_question_codes)}")
        
        if len(course_codes) > 1:
            raise InvalidFileContentException(f"File đáp án của sinh viên có các câu không thuộc cùng 1 môn học: {', '.join(course_codes)}")
 
        return data