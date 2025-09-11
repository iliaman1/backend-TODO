import os

import django
import factory
import pytest
from apps.project.models import Project, Task
from django.contrib.auth import get_user_model
from django.core.management import call_command
from factory.django import DjangoModelFactory

User = get_user_model()


@pytest.fixture(scope="session")
def django_db_setup():
    """Создаёт структуру БД перед запуском тестов."""
    call_command("migrate")


@pytest.fixture(autouse=True)
def cleanup_db(db):
    """Очищает БД после каждого теста."""
    yield
    from django.db import connection

    connection.close()
    call_command("flush", "--noinput")


def pytest_configure():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()


@pytest.fixture
def user():
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="testpass123"
    )


class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = Project

    name = "test-project"
    description = "test description"
    status = Project.Status.ACTIVE
    owner = factory.SubFactory("apps.project.tests.conftest.user")


class TaskFactory(DjangoModelFactory):
    class Meta:
        model = Task

    title = "test-task"
    description = "Test task description"
    project = factory.SubFactory(ProjectFactory)
    status = Task.Status.TODO
    priority = Task.Priority.MEDIUM
