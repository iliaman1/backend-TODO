from django.db import models
from core.models import BaseModel
from django.utils.translation import gettext_lazy as _


class Task(BaseModel):
    title = models.CharField(max_length=128, verbose_name=_('Название'), unique=True)
    description = models.TextField(verbose_name=_('описание'))
