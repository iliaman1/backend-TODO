from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.status import HTTP_404_NOT_FOUND
from rest_framework.viewsets import ModelViewSet

from .models import Project, Task
from .paginators import TaskAndProjectPaginator
from .serializers import ProjectSerializer, TaskSerializer


class TaskViewSet(ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ["created_at", "title"]
    ordering = ["-created_at"]
    pagination_class = TaskAndProjectPaginator

    def get_queryset(self):
        queryset = super().get_queryset()
        title = self.request.query_params.get("title")
        status = self.request.query_params.get("status")
        project_name = self.kwargs.get("project_name")

        if project_name:
            project = Project.objects.get(name=self.kwargs["project_name"])
            queryset = Task.objects.filter(project=project)
            task_title = self.kwargs.get("task_title")
            if task_title:
                return queryset.filter(title=self.kwargs["task_title"])

            return queryset

        if title:
            queryset = queryset.filter(title__icontains=title)
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_queryset().get()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Task.DoesNotExist:
            return Response({"error": "Task not found"}, status=HTTP_404_NOT_FOUND)


class ProjectViewSet(ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    lookup_field = "name"
    pagination_class = TaskAndProjectPaginator

    def get_object(self):
        return self.queryset.get(name=self.kwargs["name"])
