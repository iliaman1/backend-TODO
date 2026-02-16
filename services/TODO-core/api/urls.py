from apps.project.views import (
    AnalyticsDataViewSet,
    InvitationViewSet,
    ProjectViewSet,
    TaskViewSet,
)
from django.http import JsonResponse
from django.urls import include, path
from rest_framework.routers import DefaultRouter

# Создаем единый роутер для корневого API
router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"tasks", TaskViewSet, basename="task")
router.register(r"invitations", InvitationViewSet, basename="invitation")
router.register(r"analytics-data", AnalyticsDataViewSet, basename="analytics-data")


def health_check(request):
    return JsonResponse({"status": "ok"})


# Основные URL-паттерны
urlpatterns = [
    # Health check endpoint
    path("health/", health_check, name="health-check"),
    # Включаем URL, сгенерированные роутером (для /projects/ и /tasks/)
    path("", include(router.urls)),
    # Включаем кастомные URL для задач внутри проектов
    path(
        "projects/<slug:project_name>/tasks/",
        TaskViewSet.as_view({"get": "list"}),
        name="project-tasks",
    ),
    path(
        "projects/<slug:project_name>/tasks/<slug:task_title>/",
        TaskViewSet.as_view({"get": "retrieve"}),
        name="project-task-detail",
    ),
    path(
        "projects/<slug:project_name>/invite/",
        ProjectViewSet.as_view({"post": "invite"}),
        name="project-invite",
    ),
]
