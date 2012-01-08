from django.views.generic.edit import (BaseFormView, 
                                       CreateView, 
                                       UpdateView, 
                                       DeleteView,
                                       FormView,
                                       ProcessFormView)

from django.forms import Form

from django.views.generic.edit import TemplateResponseMixin, FormView
from django.template.response import TemplateResponse

from feincms.page.extensions.variative_renderer.renderers import (BaseRenderer, 
                                                TemplateResponseRendererMixin)

class ProcessPublicFormView(BaseRenderer, 
                            TemplateResponseRendererMixin, 
                            FormView):
    def show(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        return self.render_to_response(self.get_context_data(form=form))

    def get_form_kwargs(self, *args, **kwargs):
        ret = super(ProcessPublicFormView, self).get_form_kwargs(*args, 
                                                                 **kwargs)
        if not self.is_request_owner(self.request):
            'data' in ret and ret.pop('data')
            'files' in ret and ret.pop('files')
        return ret

class BasePublicForm(BaseRenderer, 
                     TemplateResponseRendererMixin, 
                     TemplateResponseMixin):
    base_to_default = False
    #renderer used when current renderer is not data owner
    process_view = ProcessPublicFormView
    success_action = False
    def prepare_page(self, request):
        if hasattr(request, '_feincms_page'):
            self.page = request._feincms_page
            self.page.contains_forms = True
    
    def get_process_renderer_args(self):
        return ()

    def get_process_renderer_kwargs(self):
        return {}
    

    def get_success_url(self):
        if getattr(self, 'success_action', False):
            if getattr(self, 'success_url', None) is None:
                self.success_url = self.page._cached_url
            return self.success_url and self.success_url \
                    or self.object.get_absolute_url()
        else:
            return None


    def get_process_renderer(self):
        if not hasattr(self, 'process_renderer'):
            self.process_renderer = \
                        type('NotOwner_%s'%self.__class__.__name__,
                                (self.process_view, self.__class__),
                                {'__doc__':getattr(self.__class__, 
                                                   '__doc__', 
                                                   None),
                                '__module__':self.__class__.__module__,
                                'instance':self.instance,
                                # 'page_view':self.page_view,
                                'object':self.object,
                                'model':self.model,
                                'success_url':self.success_url,
                                'request':self.request,
                                })(*self.get_process_renderer_args(),
                                   **self.get_process_renderer_kwargs())
        return self.process_renderer

    def process(self, request, **kwargs):
        self.object = self.instance.content_object
        self.model = self.instance.content_type.model_class()
        self.request = request
        self.prepare_page(request)
        process_renderer = self.get_process_renderer()
        if not self.is_request_owner(request):

            def render(self, request, **kwargs):
                self.request = request
                return getattr(self, request.method.lower())(request, 
                                                             **kwargs)
            
            self.render = render.__get__(process_renderer, 
                                         process_renderer.__class__)
            def finalize(self, request, response):
                pass
                

            self.finalize = finalize.__get__(process_renderer, 
                                             process_renderer.__class__)
            
            process_renderer.get = process_renderer.show
            process_renderer.post = process_renderer.show
            process_renderer.put = process_renderer.show
            process_renderer.delete = process_renderer.show
    
    def render(self, request, **kwargs):
        getattr(self, request.method.lower())(request, **kwargs)
        return self.get_process_renderer().show(request, **kwargs)

        
    def get_form(self, *args, **kwargs):
        if not hasattr(self, '_form'):
            self._form = super(BasePublicForm, self).get_form(*args, 
                                                              **kwargs)
        return self._form

    def finalize(self, request, response):
        if self.get_success_url() and self.is_request_owner(request):
            form = self.get_form(self.get_form_class())
            if form.is_valid():
                return self.form_valid(form)

    def is_request_owner(self, request):
        return self.get_submit_name() in request.REQUEST

    def get_formdata_prefix(self):
        return '%s_%s_%s'%(self.instance.parent.slug, 
                           self.instance.region, 
                           self.instance.ordering)

    def get_submit_name(self):
        return unicode(''.join((self.get_formdata_prefix(),
                                self.template_name_suffix)))

    def get_object(self):
        return self.object

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super(BasePublicForm, self).get_form_kwargs(*args, 
                                                               **kwargs)
        form_kwargs.update({'prefix':self.get_formdata_prefix()})
        return form_kwargs

    def get_form(self, form_class):
        if form_class:
            form = super(BasePublicForm, self).get_form(form_class)
            form.submit_name = self.get_submit_name()
            return form


class CreatePublicForm(BasePublicForm, CreateView):
    '''Create'''
    template_name_suffix = '_create'

    def get_object(self):
        pass


class UpdatePublicForm(BasePublicForm, UpdateView):
    '''Update'''
    template_name_suffix = '_update'


class DeletePublicForm(BasePublicForm, DeleteView):
    '''Delete'''
    template_name_suffix = '_delete'

    def get_form_class(self, *args, **kwargs):
        class DummyDeleteForm(object):
            def is_valid(self, *args, **kwargs):
                return True
            def __unicode__(self):
                return u''
        return DummyDeleteForm
    
    def get_form(self, form_class):
        if form_class:
            form = form_class()
            form.submit_name = self.get_submit_name()
            return form

    def form_valid(self, form):
        return self.delete(self.request)