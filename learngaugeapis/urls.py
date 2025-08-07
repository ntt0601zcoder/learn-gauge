from django.urls import path, include
from rest_framework.routers import SimpleRouter

from learngaugeapis.views.anonymous import AnonymousView
from learngaugeapis.views.auth import AuthView
from learngaugeapis.views.health import HealthCheckView
from learngaugeapis.views.root_user import RootUserView
from learngaugeapis.views.student import StudentView
from learngaugeapis.views.user import UserView

router = SimpleRouter(trailing_slash=False)

router.register('auth', AuthView, "auth")
router.register('root/users', RootUserView, "root_users")
router.register('users', UserView, "users")
router.register('users', AnonymousView, "anonymous_users")
router.register('students', StudentView, "students")

urlpatterns = [
   path('', include(router.urls)),
   path('health/', HealthCheckView.as_view(), name='health-check'),
]