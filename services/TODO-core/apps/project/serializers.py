from rest_framework import serializers

from .models import Project, Task


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ("name", "description", "status", "owner_id", "members", "created_at")
        read_only_fields = ("owner_id",)
        lookup_field = "name"
        extra_kwargs = {"url": {"lookup_field": "name"}}


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
