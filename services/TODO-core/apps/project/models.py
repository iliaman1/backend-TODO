from core.models import BaseModel
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Project(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "Active", "Активный"
        ARCHIVED = "Archived", "Архивный"
        COMPLETED = "Completed", "Завершенный"

    name = models.SlugField(max_length=128, verbose_name=_("Название"), unique=True)
    description = models.TextField(verbose_name=_("Описание"), blank=True)
    status = models.CharField(
        verbose_name=_("Статус"),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="owned_projects",
        verbose_name=_("Владелец"),
    )
    members = models.ManyToManyField(
        User, related_name="projects", verbose_name=_("Участники"), blank=True
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Проект")
        verbose_name_plural = _("Проекты")


class Task(BaseModel):
    class Priority(models.TextChoices):
        LOW = "Low", "Низкий"
        MEDIUM = "Medium", "Средний"
        HIGH = "High", "Высокий"

    class Status(models.TextChoices):
        TODO = "To do", "К выполнению"
        IN_PROGRESS = "In progress", "В работе"
        REVIEW = "Review", "На проверке"
        DONE = "Done", "Завершено"

    title = models.SlugField(max_length=128, verbose_name=_("Название"))
    description = models.TextField(verbose_name=_("Описание"), blank=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="project",
        verbose_name=_("Проект"),
    )
    status = models.CharField(
        verbose_name=_("Статус"),
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
    )
    priority = models.CharField(
        verbose_name=_("Приоритет"),
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    due_date = models.DateField(
        verbose_name=_("Срок выполнения"), null=True, blank=True
    )

    def __str__(self):
        return f"{self.title} {self.project}"

    class Meta:
        verbose_name = _("Задача")
        verbose_name_plural = _("Задачи")
        ordering = ["-priority", "due_date"]
        unique_together = ("project", "title")
