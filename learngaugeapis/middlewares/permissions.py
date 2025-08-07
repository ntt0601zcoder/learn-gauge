from rest_framework import permissions
from learngaugeapis.models.user import UserRole

class IsRoot(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role == UserRole.ROOT

class IsNotRoot(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role != UserRole.ROOT
    
class IsStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role == UserRole.STUDENT
    
class IsTeacher(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role == UserRole.TEACHER