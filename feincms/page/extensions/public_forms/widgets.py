from django import forms
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from . import settings

class MixinBasedWidget(forms.widgets.Widget):
    def __init__(self, **kwargs):
        for key, value in kwargs.iteritems():
            setattr(self, key, value)
        super(MixinBasedWidget, self).__init__(attrs=kwargs.get('attrs', None))


class TemplateWidgetMixin(object):
    def get_template_names(self):
        if isinstance(self.templates, basestring):
            self.templates = [self.templates,]
        return self.templates
    
    def get_context_data(self):
        if hasattr(self, 'request'):
            context = RequestContext(self.request, self.__dict__)
        else:
            context = self.__dict__
        return context

    def render(self, name, value, attrs=None):
        return mark_safe(unicode(render_to_string(self.get_template_names(), 
                                self.get_context_data())))

class TemplateWidget(TemplateWidgetMixin, MixinBasedWidget):
    pass

class AjaxInitWidget(TemplateWidgetMixin, MixinBasedWidget):
    is_hidden = True
    class Media:
        js = (settings.MOOTOOLS, 
              settings.MOOTOOLS['forms'],
              settings.STATIC_URL+'js/form_ajax_init.js')
    
    templates = [settings.CMS_PUBLIC_FORMS_AJAX_INIT_TEMPLATE,]