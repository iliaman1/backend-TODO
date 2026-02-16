from datetime import datetime, timedelta, timezone

import jwt
import requests
from core.permissions import IsServiceUser
from django.conf import settings
from django.db.models import Count, Q
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import BasePermission, IsAuthenticated
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

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        # Если статус меняется на 'Done' и completed_at еще не установлен
        if (
            "status" in request.data
            and request.data["status"] == "Done"
            and not instance.completed_at
        ):
            instance.completed_at = datetime.now(timezone.utc)

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)


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


class AnalyticsDataViewSet(viewsets.ViewSet):
    permission_classes = [IsServiceUser]  # Защита всех эндпоинтов в этом ViewSet

    def _get_user_email_from_auth_service(self, user_id):
        # Внутренняя функция для получения email пользователя из auth-api
        service_token = settings.SERVICE_TOKEN
        if not service_token:
            return None  # Или поднять исключение

        headers = {"Authorization": f"Bearer {service_token}"}
        auth_service_url = settings.AUTH_SERVICE_URL

        try:
            response = requests.post(
                f"{auth_service_url}/internal/users/by_ids",
                json={"user_ids": [user_id]},
                headers=headers,
                timeout=5,
            )
            response.raise_for_status()
            users_data = response.json()
            if users_data:
                return users_data[0]["email"]
        except requests.RequestException as e:
            print(f"Error fetching user email for {user_id}: {e}")
        return None

    @action(detail=False, methods=["get"], url_path="user-projects")
    def user_projects(self, request):
        """
        Возвращает список проектов, в которых пользователь участвует (владелец или участник).
        Принимает user_id в Query Params.
        """
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"error": "user_id is required"}, status=400)

        projects = Project.objects.filter(
            Q(owner_id=user_id) | Q(members__contains=[user_id])
        )

        # Добавляем дополнительную информацию, если требуется для аналитики
        enriched_projects = []
        for project in projects:
            member_emails = []
            for member_id in project.members:
                email = self._get_user_email_from_auth_service(member_id)
                if email:
                    member_emails.append({"id": member_id, "email": email})

            owner_email = self._get_user_email_from_auth_service(project.owner_id)

            enriched_projects.append(
                {
                    "id": project.id,
                    "name": project.name,
                    "description": project.description,
                    "status": project.status,
                    "owner_id": project.owner_id,
                    "owner_email": owner_email,
                    "members": member_emails,
                    "created_at": project.created_at,
                }
            )

        return Response(enriched_projects)

    @action(detail=False, methods=["get"], url_path="project-stats")
    def project_stats(self, request):
        """
        Возвращает статистику по конкретному проекту:
        количество задач по статусам, количество участников, среднее время выполнения.
        Принимает project_id в Query Params.
        """
        project_id = request.query_params.get("project_id")
        if not project_id:
            return Response({"error": "project_id is required"}, status=400)

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({"error": "Project not found"}, status=404)

        # Количество участников
        # Учитываем, что owner_id - это тоже член проекта, но не в списке members
        member_count = len(project.members) + 1

        # Статусы задач
        task_statuses = (
            Task.objects.filter(project=project)
            .values("status")
            .annotate(count=Count("status"))
        )
        status_counts = {item["status"]: item["count"] for item in task_statuses}

        # Среднее время выполнения задач
        # Только для задач в статусе 'Done'
        completed_tasks = Task.objects.filter(
            project=project,
            status="Done",
            created_at__isnull=False,
            completed_at__isnull=False,
        )

        total_time_diff = timedelta(seconds=0)
        task_count = 0
        for task in completed_tasks:
            # Убедитесь, что completed_at и created_at являются datetime объектами
            if isinstance(task.completed_at, datetime) and isinstance(
                task.created_at, datetime
            ):
                time_diff = task.completed_at - task.created_at
                total_time_diff += time_diff
                task_count += 1

        avg_completion_time = (
            (total_time_diff / task_count).total_seconds() / 3600 / 24
            if task_count > 0
            else 0
        )  # В днях

        return Response(
            {
                "project_id": project.id,
                "project_name": project.name,
                "member_count": member_count,
                "task_statuses": status_counts,
                "avg_completion_time_days": avg_completion_time,
            }
        )

    @action(detail=False, methods=["get"], url_path="user-tasks-completed-last-week")
    def user_tasks_completed_last_week(self, request):
        """
        Возвращает количество задач, выполненных пользователем за последнюю неделю по всем проектам.
        Принимает user_id в Query Params.
        """
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"error": "user_id is required"}, status=400)

        one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)

        # Находим все проекты пользователя
        user_projects = Project.objects.filter(
            Q(owner_id=user_id) | Q(members__contains=[user_id])
        )

        # Считаем задачи в этих проектах
        completed_tasks_count = Task.objects.filter(
            project__in=user_projects,
            status="Done",
            completed_at__gte=one_week_ago,
            # assigned_to_id=user_id # Если есть такое поле для исполнителя задачи
        ).count()

        return Response(
            {
                "user_id": user_id,
                "tasks_completed_last_week": completed_tasks_count,
            }
        )
