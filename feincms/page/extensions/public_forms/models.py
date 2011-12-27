
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from . import settings

# Create your models here.



class PublicForm(models.Model):
    class Meta:
        abstract = True

    renderer_choices = ['feincms.page.extensions.public_forms.renderers.CreatePublicForm',
                        'feincms.page.extensions.public_forms.renderers.UpdatePublicForm',
                        'feincms.page.extensions.public_forms.renderers.DeletePublicForm',]

    enable_captcha = models.BooleanField(default=settings.PUBLIC_FORMS_DEFAULT_ENABLE_CAPTCHA)
    enable_ajax = models.BooleanField(default=settings.PUBLIC_FORMS_DEFAULT_ENABLE_AJAX)
    
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_type = models.ForeignKey(ContentType)
    content_object = generic.GenericForeignKey('content_type', 'object_id')


def register(cls, admin_cls):
    cls.create_content_type(PublicForm)