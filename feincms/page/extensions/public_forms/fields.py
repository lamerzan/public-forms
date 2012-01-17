from django.forms import Field
from .widgets import TemplateWidget, AjaxInitWidget


class TemplateRenderField(Field):
    django_field_valid_kwargs =  ['required', 'widget', 'label', 'initial', 
                                  'help_text', 'error_messages', 
                                  'show_hidden_initial', 'validators', 
                                  'localize']

    widget_class = TemplateWidget

    def remove_invalid_kwgars(self, kwargs):
        removed_keys = []

        for key in kwargs:
            if not key in self.django_field_valid_kwargs:
                removed_keys += key,

        for key in removed_keys:
            kwargs.pop(key, None)

        return kwargs

    def __init__(self, *args, **kwargs):
        kwargs['required'] = False
        self.widget = self.widget_class(**kwargs)
        self.remove_invalid_kwgars(kwargs)
        super(TemplateRenderField, self).__init__(*args, **kwargs)

class AjaxInitField(TemplateRenderField):
    widget_class = AjaxInitWidget