
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.forms import Media

from . import settings

# Create your models here.



class PublicForm(models.Model):
    @property
    def media(self):
        if not hasattr(self, '_media'):
            self._media = getattr(self, 'content_media', Media())
            renderer_media = self.render.get_media()
            if renderer_media:
                self._media.add_js(renderer_media._js)
                self._media.add_css(renderer_media._css)
        return self._media
    
    class Meta:
        abstract = True

    renderer_choices = ['feincms.page.extensions.public_forms.renderers.CreatePublicForm',
                        'feincms.page.extensions.public_forms.renderers.UpdatePublicForm',
                        'feincms.page.extensions.public_forms.renderers.DeletePublicForm',]

    enable_captcha_once = models.BooleanField(default=settings.PUBLIC_FORMS_DEFAULT_ENABLE_CAPTCHA_ONCE)
    enable_captcha_always = models.BooleanField(default=settings.PUBLIC_FORMS_DEFAULT_ENABLE_CAPTCHA_ALWAYS)

    enable_ajax = models.BooleanField(default=settings.PUBLIC_FORMS_DEFAULT_ENABLE_AJAX)
    
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_type = models.ForeignKey(ContentType)
    content_object = generic.GenericForeignKey('content_type', 'object_id')


def register(cls, admin_cls):
    cls.create_content_type(PublicForm)

from feincms.module.page.models import Page
Page.register_templates({
        'title': 'Testing template',
        'path': 'cms/3cols.html',
        'regions': (
            ('first_col', 'First column'),
            ('second_col', 'Second column'),
            ('third_col', 'Third column'),
            ),
        })