import pytest
from apps.project.models import Project, Task
from apps.project.tests.conftest import ProjectFactory, TaskFactory
from django.core.exceptions import ValidationError


@pytest.mark.django_db
def test_project_creation(user):
    """Тест создания проекта с валидными данными."""
    project = Project.objects.create(
        name="awesome-project",
        description="My awesome project",
        status=Project.Status.ACTIVE,
        owner=user,
    )
    assert project.name == "awesome-project"
    assert project.status == Project.Status.ACTIVE
    assert project.owner == user
    assert str(project) == "awesome-project"


@pytest.mark.django_db
def test_project_slugfield_validation(user):
    """Тест валидации SlugField (только латиница, цифры и дефисы)."""
    with pytest.raises(ValidationError):
        project = Project(name="Неправильное имя!", owner=user)
        project.full_clean()


@pytest.mark.django_db
def test_project_unique_name(user):
    """Тест уникальности имени проекта."""
    Project.objects.create(name="unique-project", owner=user)
    with pytest.raises(ValidationError):
        Project(name="unique-project", owner=user).full_clean()


@pytest.mark.django_db
def test_project_status_choices(user):
    """Тест доступных статусов проекта."""
    project = ProjectFactory(status=Project.Status.ARCHIVED)
    assert project.status in Project.Status.values


@pytest.mark.django_db
def test_project_members(user):
    """Тест добавления участников проекта."""
    project = ProjectFactory()
    project.members.add(user)
    assert user in project.members.all()


@pytest.mark.django_db
def test_task_creation():
    """Тест создания задачи."""
    task = TaskFactory()
    assert task.title == "test-task"
    assert task.status == Task.Status.TODO
    assert task.priority == Task.Priority.MEDIUM
    assert str(task) == "test-task test-project"


@pytest.mark.django_db
def test_task_unique_together():
    """Тест уникальности задачи в рамках проекта."""
    task = TaskFactory(title="unique-task")
    with pytest.raises(ValidationError):
        TaskFactory(project=task.project, title="unique-task")


@pytest.mark.django_db
def test_task_priority_choices():
    """Тест доступных приоритетов задачи."""
    task = TaskFactory(priority=Task.Priority.HIGH)
    assert task.priority in Task.Priority.values


@pytest.mark.django_db
def test_task_status_flow():
    """Тест изменения статуса задачи."""
    task = TaskFactory(status=Task.Status.TODO)
    task.status = Task.Status.IN_PROGRESS
    task.save()
    assert task.status == Task.Status.IN_PROGRESS


@pytest.mark.django_db
def test_task_due_date_optional():
    """Тест необязательности поля due_date."""
    task = TaskFactory(due_date=None)
    assert task.due_date is None


@pytest.mark.parametrize("status", Task.Status.values)
@pytest.mark.django_db
def test_task_all_statuses(status):
    """Тест всех возможных статусов задачи."""
    task = TaskFactory(status=status)
    assert task.status == status


@pytest.mark.django_db
def test_task_ordering():
    """Тест сортировки задач по приоритету и сроку."""
    project = ProjectFactory()
    task1 = TaskFactory(project=project, priority=Task.Priority.HIGH, due_date=None)
    task2 = TaskFactory(
        project=project, priority=Task.Priority.MEDIUM, due_date="2023-01-01"
    )
    tasks = list(project.project.all())  # project.project - related_name из Task
    assert tasks == [task1, task2]
