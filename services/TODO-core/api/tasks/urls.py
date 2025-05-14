from django.urls import path, include
from rest_framework import routers

from apps.tasks.views import TaskViewSet

router = routers.DefaultRouter()
router.register(r'task', TaskViewSet, basename='task')

urlpatterns = [
    path('', include(router.urls)),
]
