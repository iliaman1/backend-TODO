from apps.project.views import ProjectViewSet, TaskViewSet
from django.urls import include, path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"tasks", TaskViewSet, basename="task")

urlpatterns = [
    path("", include(router.urls)),
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
]
