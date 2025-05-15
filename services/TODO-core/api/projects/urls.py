from django.urls import path, include
from rest_framework import routers

from apps.project.views import ProjectViewSet, TaskViewSet

router = routers.DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')

urlpatterns = [
    path('', include(router.urls)),
    path('projects/<slug:project_name>/tasks/', TaskViewSet.as_view({'get': 'list'}), name='project-tasks'),
    path(
        'projects/<slug:project_name>/tasks/<slug:task_title>/',
        TaskViewSet.as_view({'get': 'retrieve'}),
        name='project-task-detail'
    ),
]
