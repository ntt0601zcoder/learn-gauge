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
from learngaugeapis.const.exam_formats import ExamFormat
from learngaugeapis.serializers.exam_results import UploadEssayExamResultSerializer
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
from learngaugeapis.models.essay_exam_result import EssayExamResult

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
            ),
            openapi.Parameter(
                name="class",
                in_="query",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                name="course",
                in_="query",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                name="clo_type",
                in_="query",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                name="start_year",
                in_="query",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                name="semester",
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

            class_id = request.query_params.get("class", None)
            if class_id:
                exams = exams.filter(course_class__id=class_id)

            course_id = request.query_params.get("course", None)
            if course_id:
                exams = exams.filter(course_class__course__id=course_id)

            clo_type_id = request.query_params.get("clo_type", None)
            if clo_type_id:
                exams = exams.filter(clo_type__id=clo_type_id)

            start_year = request.query_params.get("start_year", None)
            if start_year:
                exams = exams.filter(course_class__year=start_year)

            semester = request.query_params.get("semester", None)
            if semester:
                exams = exams.filter(course_class__semester=semester)

            serializer = ExamSerializer(exams, many=True)
            return RestResponse(
                status=status.HTTP_200_OK, 
                data={
                    "exams": serializer.data,
                    "full": self.__get_full_exam_data(serializer.data)
                }
            ).response
        except Exception as e:
            logging.getLogger().error("ExamView.list exc=%s", str(e))
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response

    def __get_full_exam_data(self, dataset):
        total_students = sum(data["metadata"]["total_students"] for data in dataset)
        total_passed = sum(data["metadata"]["total_passed"] for data in dataset)
        total_A = sum(data["metadata"]["clo_classification"]["A"]["count"] for data in dataset)
        total_B = sum(data["metadata"]["clo_classification"]["B"]["count"] for data in dataset)
        total_C = sum(data["metadata"]["clo_classification"]["C"]["count"] for data in dataset)
        total_D = sum(data["metadata"]["clo_classification"]["D"]["count"] for data in dataset)
        total_F = sum(data["metadata"]["clo_classification"]["F"]["count"] for data in dataset)

        data = {
            "total_students": total_students,
            "pass_rate": total_passed / total_students * 100,
            "clo_classification": {
                "A": {
                    "count": total_A,
                    "percentage": total_A / total_students * 100
                },
                "B": {
                    "count": total_B,
                    "percentage": total_B / total_students * 100
                },
                "C": {
                    "count": total_C,
                    "percentage": total_C / total_students * 100
                },
                "D": {
                    "count": total_D,
                    "percentage": total_D / total_students * 100
                },
                "F": {
                    "count": total_F,
                    "percentage": total_F / total_students * 100
                }
            }
        }
        return data
        
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

            course: Course  = Course.objects.get(classes=validated_data['course_class'])

            if not course.clo_types.filter(is_evaluation=True, deleted_at=None).exists():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, message="Vui lòng cài đặt CLO đánh giá cho khóa học trước khi thực hiện thao tác này!").response

            answer_file = validated_data.pop('answer_file')
            classification_file = validated_data.pop('classification_file')
            student_answer_file = validated_data.pop('student_answer_file')

            answer_data = self.__load_and_validate_answer_file(course.code, answer_file)
            classification_data = self.__load_and_validate_classification_file(course.code, classification_file)
            student_answer_data = self.__load_and_validate_student_answer_file(course.code, student_answer_file)

            self.__validate_exam_result_data(course.code, answer_data, classification_data, student_answer_data)
            self.__consolidate_exam_result_data(validated_data["chapters"], answer_data, classification_data, student_answer_data)

            with transaction.atomic():
                exam = Exam.objects.create(
                    course_class=validated_data['course_class'],
                    name=validated_data["name"],
                    description=validated_data["description"],
                    clo_type=validated_data["clo_type"],
                    exam_format=ExamFormat.MCQ.value,
                    chapters=validated_data["chapters"],
                    pass_expectation_rate=validated_data["pass_expectation_rate"],
                    clo_pass_threshold=validated_data["clo_pass_threshold"],
                    max_score=validated_data["max_score"],
                )

                exam_results = []

                for student_code, student_data in student_answer_data.items():
                    exam_results.append(
                        ExamResult(
                            student_code=student_code,
                            student_name=student_data["student_name"],
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

                if len(exam_results) == 0:
                    raise InvalidFileContentException("Không có sinh viên nào tham gia thi!")
                
                ExamResult.objects.bulk_create(exam_results)
            return RestResponse(status=status.HTTP_200_OK, data=ExamSerializer(exam).data).response
        except Course.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND, data="Không tìm thấy học phần tương ứng!").response
        except InvalidFileContentException as e:
            return RestResponse(status=status.HTTP_400_BAD_REQUEST, message=str(e)).response
        except Exception as e:
            logging.getLogger().error("ExamView.upload_exam_results exc=%s", str(e))
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response

    def __consolidate_exam_result_data(self, chapters, answer_data, classification_data, student_answer_data):
        for _, student_data in student_answer_data.items():
            student_data["number_of_correct_easy_questions"] = 0
            student_data["number_of_correct_medium_questions"] = 0
            student_data["number_of_correct_hard_questions"] = 0
            student_data["number_of_correct_questions"] = 0
            student_data["number_of_easy_questions"] = 0
            student_data["number_of_medium_questions"] = 0
            student_data["number_of_hard_questions"] = 0
            student_data["number_of_dropped_questions"] = 0

            for question_code, answer in student_data['answers'].items():
                chapter_code = question_code[:-4]

                if chapter_code not in classification_data or classification_data[chapter_code] not in chapters:
                    student_data["number_of_dropped_questions"] += 1
                    continue

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

        number_of_dropped_questions_set = set()

        for _, student_data in student_answer_data.items():
            number_of_dropped_questions_set.add(student_data["number_of_dropped_questions"])

        if len(number_of_dropped_questions_set) > 1:
            raise InvalidFileContentException("Số lượng câu hỏi bị loại trừ của sinh viên không tương đồng!")

    def __validate_exam_result_data(self, course_code, answer_data, classification_data, student_answer_data):
        # if len(answer_data["questions"]) != len(classification_data):
        #     raise InvalidFileContentException("Số lượng câu hỏi trong file đáp án và file câu hỏi - chương không khớp!")

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

            _course_code = row['question_code'][:-8].lower()

            if _course_code != course_code.lower():
                invalid_question_codes.add(row['question_code'])

            course_codes.add(_course_code)

            data["questions"][row['question_code']] = {
                "correct_answer": row['correct_answer'],
                "difficulty": row['question_code'][-1].lower(),
                "no": row['question_code'][-4:-1].lower(),
                "version": row['question_code'][-8:-4].lower(),
                "course_code": _course_code,
            }
            
            if row['question_code'][-8:-4].lower() not in data["exams"]:
                data["exams"][row['question_code'][-8:-4].lower()] = {
                    "number_of_questions": 1,
                }
            else:
                data["exams"][row['question_code'][-8:-4].lower()]["number_of_questions"] += 1

        all_exams_have_same_number_of_questions = all(data["exams"][exam]["number_of_questions"] == data["exams"][list(data["exams"].keys())[0]]["number_of_questions"] for exam in data["exams"])

        # if not all_exams_have_same_number_of_questions:
        #     raise InvalidFileContentException(f"Các mã đề thi có số lượng câu hỏi không tương đồng!")

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
        df = df.rename(columns={'mã đề': 'exam_version_code', 'chương': 'chapter'})

        data = {}
        duplicate_exam_version_codes = set()
        course_codes = set()
        invalid_exam_version_codes = set()

        for _, row in df.iterrows():
            if row['exam_version_code'] in data:
                duplicate_exam_version_codes.add(row['exam_version_code'])
                continue

            _course_code = row['exam_version_code'][:-4].lower()

            if _course_code != course_code.lower():
                invalid_exam_version_codes.add(_course_code)

            course_codes.add(_course_code)
            data[row['exam_version_code']] = row['chapter']

        if duplicate_exam_version_codes:
            raise InvalidFileContentException(f"File câu hỏi - chương có {len(duplicate_exam_version_codes)} mã đề hỏi bị trùng lặp: {', '.join(duplicate_exam_version_codes)}")

        if invalid_exam_version_codes:
            raise InvalidFileContentException(f"File câu hỏi - chương có các mã đề không thuộc môn học {course_code}: {', '.join(invalid_exam_version_codes)}")
        
        if len(course_codes) > 1:
            raise InvalidFileContentException(f"File câu hỏi - chương có các mã đề không thuộc cùng 1 môn học: {', '.join(course_codes)}")

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
            data[student_id]["student_name"] = row['student_name']
            data[student_id]["answers"] = answers
            data[student_id]["number_of_questions"] = len(answers)

            for question_code, answer in answers.items():
                _course_code = question_code[:-8].lower()

                if _course_code != course_code.lower():
                    invalid_question_codes.add(question_code)

                course_codes.add(_course_code)
                version.add(question_code[-8:-4].lower())

            # if len(version) > 1:
            #     raise InvalidFileContentException(f"File đáp án của sinh viên {student_id} có các câu không thuộc cùng 1 mã đề thi: {', '.join(version)}")

        if student_ids:
            raise InvalidFileContentException(f"Có {len(student_ids)} mã sinh viên bị trùng lặp: {student_ids.join(', ')}")

        if invalid_question_codes:
            raise InvalidFileContentException(f"File đáp án của sinh viên có các câu không thuộc môn học {course_code}: {', '.join(invalid_question_codes)}")
        
        if len(course_codes) > 1:
            raise InvalidFileContentException(f"File đáp án của sinh viên có các câu không thuộc cùng 1 môn học: {', '.join(course_codes)}")
 
        return data

    @swagger_auto_schema(request_body=UploadEssayExamResultSerializer)
    @action(detail=False, methods=['post'], url_path='upload-essay-exam-results', parser_classes=[MultiPartParser])
    def upload_essay_exam_results(self, request):
        try:
            logging.getLogger().info("ExamView.upload_essay_exam_results req=%s", request.data)
            serializer = UploadEssayExamResultSerializer(data=request.data)

            if not serializer.is_valid():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors).response

            validated_data = serializer.validated_data
            
            course: Course  = Course.objects.get(classes=validated_data['course_class'])

            if not course.clo_types.filter(is_evaluation=True, deleted_at=None).exists():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, message="Vui lòng cài đặt CLO đánh giá cho khóa học trước khi thực hiện thao tác này!").response

            essay_exam_result_file = validated_data.pop('essay_exam_result_file')
            essay_exam_result_data = self.__load_and_validate_essay_exam_result_file(
                course.code, essay_exam_result_file, validated_data["chapters"]
            )
            
            with transaction.atomic():
                exam = Exam.objects.create(
                    course_class=validated_data['course_class'],
                    name=validated_data["name"],
                    description=validated_data["description"],
                    clo_type=validated_data["clo_type"],
                    exam_format=ExamFormat.ESSAY.value,
                    chapters=validated_data["chapters"],
                    pass_expectation_rate=validated_data["pass_expectation_rate"],
                    clo_pass_threshold=validated_data["clo_pass_threshold"],
                    max_score=validated_data["max_score"],
                )
                essay_exam_results = []
                
                for student_code, student_data in essay_exam_result_data.items():
                    essay_exam_results.append(
                        EssayExamResult(
                            student_code=student_code,
                            exam=exam,
                            average_score=student_data["average_score"],
                        )
                    )
                    
                if len(essay_exam_results) == 0:
                    raise InvalidFileContentException("Không có sinh viên nào tham gia thi!")

                EssayExamResult.objects.bulk_create(essay_exam_results)
            return RestResponse(status=status.HTTP_200_OK, data=ExamSerializer(exam).data).response
        except Course.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND, data="Không tìm thấy học phần tương ứng!").response
        except InvalidFileContentException as e:
            return RestResponse(status=status.HTTP_400_BAD_REQUEST, message=str(e)).response
        except Exception as e:
            logging.getLogger().error("ExamView.upload_essay_exam_results exc=%s", str(e))
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    def __load_and_validate_essay_exam_result_file(self, course_code, file, chapters):
        df = pd.read_excel(file)
        df = df.map(lambda x: x.strip().lower() if isinstance(x, str) else x)
        df.columns = df.columns.str.strip().str.lower()

        # Chuẩn hóa tên cột: Sinh viên -> student_code
        column_mapping = {'sinh viên': 'student_code'}
        df = df.rename(columns=column_mapping)

        if 'student_code' not in df.columns:
            raise InvalidFileContentException("File phải có cột 'Sinh viên'!")

        if not chapters:
            raise InvalidFileContentException("Exam phải có ít nhất một chương được cấu hình!")

        # Xác định các cột chương cần tính (chỉ các chương trong Exam.chapters)
        chapter_columns = []
        for ch in chapters:
            col_name = f"chương {ch}"
            if col_name not in df.columns:
                raise InvalidFileContentException(f"File thiếu cột điểm cho chương {ch} ('{col_name}')!")
            chapter_columns.append(col_name)

        # Loại bỏ hàng có mã sinh viên rỗng/NaN trước khi kiểm tra trùng lặp
        df = df[df['student_code'].notna() & (df['student_code'].astype(str).str.strip() != '') & (df['student_code'].astype(str).str.strip() != 'nan')]

        # Loại bỏ hàng có mã sinh viên rỗng/NaN
        df = df[df['student_code'].notna() & (df['student_code'].astype(str).str.strip() != '')]
        df = df[df['student_code'].astype(str).str.strip() != 'nan']

        # Kiểm tra mã sinh viên trùng lặp
        duplicate_student_codes = df[df.duplicated(subset=['student_code'], keep=False)]['student_code'].unique().tolist()
        if len(duplicate_student_codes) > 0:
            raise InvalidFileContentException(
                f"File có mã sinh viên trùng lặp: {', '.join(str(c) for c in duplicate_student_codes)}"
            )

        data = {}
        for _, row in df.iterrows():
            if pd.isna(row['student_code']):
                continue
            student_code = str(row['student_code']).strip()
            if not student_code or student_code == 'nan':
                continue

            # Chỉ lấy điểm các chương được cấu hình trong Exam
            chapter_scores = row[chapter_columns].apply(pd.to_numeric, errors='coerce')
            valid_scores = chapter_scores.dropna()

            if len(valid_scores) == 0:
                raise InvalidFileContentException(
                    f"Sinh viên {student_code} không có điểm hợp lệ cho các chương {chapters}!"
                )

            average_score = float(valid_scores.mean())

            data[student_code] = {
                "average_score": round(average_score, 2),
            }

        return data
#   
