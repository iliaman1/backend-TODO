from django.contrib import admin
from .models import Project, Task


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'status', 'owner', 'created_at', 'update_at')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'project', 'status', 'priority', 'due_date', 'created_at', 'update_at')
