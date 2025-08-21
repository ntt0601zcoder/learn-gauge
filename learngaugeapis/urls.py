from django.urls import path, include
from rest_framework.routers import SimpleRouter

from learngaugeapis.views.academic_program import AcademicProgramView
from learngaugeapis.views.anonymous import AnonymousView
from learngaugeapis.views.auth import AuthView
from learngaugeapis.views.course import CourseView
from learngaugeapis.views.course_class import ClassView
from learngaugeapis.views.health import HealthCheckView
from learngaugeapis.views.major import MajorView
from learngaugeapis.views.root_user import RootUserView
from learngaugeapis.views.student import StudentView
from learngaugeapis.views.user import UserView
from learngaugeapis.views.clo_types import CLOTypeView

router = SimpleRouter(trailing_slash=False)

router.register('auth', AuthView, "auth")
router.register('root/users', RootUserView, "root_users")
router.register('users', UserView, "users")
router.register('users', AnonymousView, "anonymous_users")
router.register('students', StudentView, "students")
router.register('academic-programs', AcademicProgramView, "academic_programs")
router.register('majors', MajorView, "majors")
router.register('classes', ClassView, "classes")
router.register('courses', CourseView, "courses")
router.register('clo-types', CLOTypeView, "clo_types")

urlpatterns = [
   path('', include(router.urls)),
   path('health/', HealthCheckView.as_view(), name='health-check'),
]