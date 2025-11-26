import logging

import requests
from django.conf import settings
from rest_framework import serializers

from .models import Project, Task

logger = logging.getLogger(__name__)


class ProjectSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ("name", "description", "status", "owner_id", "members", "created_at")
        read_only_fields = ("owner_id",)
        lookup_field = "name"
        extra_kwargs = {"url": {"lookup_field": "name"}}

    def get_members(self, obj):
        if not obj.members:
            return []

        try:
            # Делаем запрос к сервису аутентификации
            # В реальном приложении здесь нужна более надежная обработка ошибок,
            # таймауты и, возможно, кэширование.
            response = requests.post(
                f"{settings.AUTH_SERVICE_URL}/internal/users/by_ids",
                json={"user_ids": obj.members},
                headers={"Authorization": f"Bearer {settings.SERVICE_TOKEN}"},
                timeout=5,
            )
            response.raise_for_status()  # Вызовет исключение для статусов 4xx/5xx
            return response.json()
        except requests.RequestException as e:
            # Если сервис аутентификации недоступен, возвращаем просто ID
            logger.warning(
                "Could not fetch members from auth service: %s", e, exc_info=True
            )
            return [{"id": user_id} for user_id in obj.members]


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = (
            "title",
            "description",
            "project",
            "status",
            "priority",
            "due_date",
            "created_at",
        )
        lookup_field = "title"
        extra_kwargs = {"url": {"lookup_field": "title"}}
