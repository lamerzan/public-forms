from importlib import import_module


from django.db import models

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.forms import Media


from . import settings

# Create your models here.

def path_represented_object(path):
    obj_module, obj_name = path.rsplit('.', 1)
    if not obj_module or not obj_name:
        raise ValueError('%s is not a valid module path'%path)
    try:
        return getattr(import_module(obj_module), obj_name)
    except AttributeError:
        raise AttributeError("'%s' object has no attribute '%s'"%(obj_module, 
                                                                  obj_name))


class ContentObjectForeignKey(generic.GenericForeignKey):
    def __get__(self, instance, owner):
        if instance and hasattr(instance, 'get_content_object'):
            return instance.get_content_object(super(ContentObjectForeignKey, 
                                                                self).__get__)
        return super(ContentObjectForeignKey, self).__get__(instance, owner)


class DynamicEditableFieldMixin(object):
    disable_on_hasattr = 'get_content_object'
    def get_editable(self):
        return not hasattr(self.model, self.disable_on_hasattr)
    
    def set_editable(self, value):
        pass
    
    def del_editable(self):
        pass
    editable = property(get_editable, set_editable, del_editable)


class FieldDefaultMixin(object):
    def modify_default(self, value):
        return value

    def get_default(self):
        cache_name = '_%s_value'%self.default_field
        if not hasattr(self, cache_name):
            default = self.modify_default(getattr(self.model, 
                                                self.default_field, 
                                                getattr(self,'_initial_default', 
                                                None)))
            setattr(self, cache_name, default)
        return getattr(self, cache_name)
    
    def set_default(self, value):
        self._initial_default = value
    
    def del_default(self):
        pass


class ObjectIdField(DynamicEditableFieldMixin, 
                           FieldDefaultMixin,
                           models.PositiveIntegerField):
    default_field = 'default_object_id'


class ContentTypeField(DynamicEditableFieldMixin, 
                       FieldDefaultMixin, 
                       models.ForeignKey):
    default_field = 'default_content_type'


    def modify_default(self, value):
        return ContentType.objects.get_for_model(value).id

from django.contrib.auth.models import Group

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
    
    object_id = ObjectIdField(blank=True, null=True)
    content_type = ContentTypeField(ContentType)
    content_object = ContentObjectForeignKey('content_type', 'object_id')


def register(cls, admin_cls):
    for model in settings.PUBLIC_FORMS_CONTENT_TYPES:
        if isinstance(model, basestring):
            model = path_represented_object(model)
        cls.create_content_type(model)