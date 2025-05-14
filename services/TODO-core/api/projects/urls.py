from django.urls import path, include
from rest_framework import routers

from apps.project.views import ProjectViewSet

router = routers.DefaultRouter()
router.register(r'project', ProjectViewSet, basename='project')

urlpatterns = [
    path('', include(router.urls)),
]
