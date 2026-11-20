from django.contrib import admin
from .models import University, Programme, CurriculumVersion, Unit, CurriculumUnit, Topic
for model in (University, Programme, CurriculumVersion, Unit, CurriculumUnit, Topic):
    admin.site.register(model)
