from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.status import HTTP_404_NOT_FOUND
from rest_framework.viewsets import ModelViewSet
from tasks import send_invitation_email

from .models import Project, Task
from .paginators import TaskAndProjectPaginator
from .serializers import ProjectSerializer, TaskSerializer


class InvitationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        # Опционально: можно добавить проверку, не является ли пользователь
        # уже участником проекта.
        return value


class IsProjectOwner(BasePermission):
    """
    Разрешение, которое проверяет, является ли пользователь владельцем проекта.
    """

    def has_object_permission(self, request, view, obj):
        return obj.owner_id == request.user.id


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

    def perform_create(self, serializer):
        serializer.save(owner_id=self.request.user.id)

    def get_object(self):
        lookup_value = self.kwargs.get("name") or self.kwargs.get("project_name")
        return self.queryset.get(name=lookup_value)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsProjectOwner],
        url_path="invite",
    )
    def invite(self, request, name=None):
        project = self.get_object()
        serializer = InvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recipient_email = serializer.validated_data["email"]

        # Создаем JWT токен для приглашения
        payload = {
            "project_id": project.id,
            "recipient_email": recipient_email,
            "inviter_id": request.user.id,
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
            "type": "invitation",
        }
        token = jwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        # Вызываем задачу Celery для отправки письма
        send_invitation_email.delay(
            recipient_email=recipient_email, project_name=project.name, token=token
        )

        return Response(
            {
                "message": f"Invitation sent to {recipient_email} for project {project.name}"
            }
        )

    def get_object(self):
        lookup_value = self.kwargs.get("name") or self.kwargs.get("project_name")
        return self.queryset.get(name=lookup_value)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsProjectOwner],
        url_path="invite",
    )
    def invite(self, request, **kwargs):
        project = self.get_object()
        serializer = InvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recipient_email = serializer.validated_data["email"]

        # Создаем JWT токен для приглашения
        payload = {
            "project_id": project.id,
            "recipient_email": recipient_email,
            "inviter_id": request.user.id,
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
            "type": "invitation",
        }
        token = jwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        # Вызываем задачу Celery для отправки письма
        send_invitation_email.delay(
            recipient_email=recipient_email, project_name=project.name, token=token
        )

        return Response(
            {
                "message": f"Invitation sent to {recipient_email} for project {project.name}"
            }
        )


class InvitationViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["post"], url_path="accept")
    def accept(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"error": "Token is required"}, status=400)

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except jwt.ExpiredSignatureError:
            return Response({"error": "Invitation has expired"}, status=400)
        except jwt.PyJWTError:
            return Response({"error": "Invalid token"}, status=400)

        if payload.get("type") != "invitation":
            return Response({"error": "Invalid token type"}, status=400)

        # Проверяем, совпадает ли email в токене с email текущего пользователя
        if payload.get("recipient_email") != request.user.email:
            return Response({"error": "This invitation is not for you"}, status=403)

        try:
            project = Project.objects.get(id=payload.get("project_id"))
        except Project.DoesNotExist:
            return Response({"error": "Project not found"}, status=404)

        # Добавляем пользователя в участники проекта
        if request.user.id in project.members:
            return Response(
                {"message": f"You are already a member of project {project.name}"}
            )

        project.members.append(request.user.id)
        project.save()

        return Response({"message": f"Successfully joined project {project.name}"})
