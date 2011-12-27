from django.views.generic.edit import (BaseFormView, 
                                       CreateView, 
                                       UpdateView, 
                                       DeleteView,
                                       FormView,
                                       ProcessFormView)

from django.views.generic.edit import TemplateResponseMixin, FormView
from django.template.response import TemplateResponse

from feincms.page.extensions.variative_renderer.renderers import (BaseRenderer, 
                                                TemplateResponseRendererMixin)

class ProcessPublicFormView(BaseRenderer, 
                            TemplateResponseRendererMixin, 
                            FormView):
    pass

class BasePublicForm(BaseRenderer, 
                     TemplateResponseRendererMixin, 
                     TemplateResponseMixin):
    base_to_default = False
    #renderer used when current renderer is not data owner
    process_view = ProcessPublicFormView
    
    def process(self, request, **kwargs):
        self.object = self.instance.content_object
        self.model = self.instance.content_type.model_class()

        if not self.is_request_owner(request):
            process_renderer = type('NotOwner_%s'%self.__class__.__name__,
                                (self.process_view, self.__class__),
                                {'__doc__':getattr(self.__class__, 
                                                   '__doc__', 
                                                   None),
                                '__module__':self.__class__.__module__,
                                })
            self.render = process_renderer.render.__get__(self, 
                                                          process_renderer)
            
    def is_request_owner(self, request):
        return unicode(''.join((self.get_formdata_prefix(),
                                self.template_name_suffix))) \
                in request.REQUEST

    def get_formdata_prefix(self):
        return '%s_%s_%s'%(self.instance.parent.slug, 
                           self.instance.region, 
                           self.instance.ordering)

class CreatePublicForm(BasePublicForm, CreateView):
    '''Create'''
    template_name_suffix = '_create'
    def get_object(self):
        pass


class UpdatePublicForm(BasePublicForm, UpdateView):
    '''Update'''
    template_name_suffix = '_update'
    def get_object(self):
        return self.object


class DeletePublicForm(BasePublicForm, DeleteView):
    '''Delete'''
    template_name_suffix = '_delete'
    def get_object(self):
        return self.object