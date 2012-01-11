from itertools import dropwhile

from django.views.generic.edit import (BaseFormView, 
                                       CreateView, 
                                       UpdateView, 
                                       DeleteView,
                                       FormView,
                                       ProcessFormView)

from django.forms import Form, ModelForm, Media

from django.views.generic.edit import TemplateResponseMixin, FormView
from django.template.response import TemplateResponse
from django.utils.translation import get_language_from_request
from django.utils.safestring import mark_safe
from django.utils import simplejson as json

from captcha.fields import ReCaptchaFieldAjax
from captcha.client import RECAPTCHA_SUPPORTED_LANUAGES

from feincms.page.extensions.variative_renderer.renderers import (BaseRenderer, 
                                                TemplateResponseRendererMixin)


from . import settings
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

    def prepare_renderer(self, request):
        self.object = self.instance.content_object
        self.model = self.instance.content_type.model_class()
        self.request = request
        self.prepare_page(request)            
    
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
            self.process_renderer.sibling = self
        return self.process_renderer

    def process(self, request, **kwargs):
        self.prepare_renderer(request)
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
            # process_renderer.get_form_class = self.get_form_class.\
            #                                  __func__.__get__(process_renderer, 
            #                                  process_renderer.__class__)
    
    def render(self, request, **kwargs):
        getattr(self, request.method.lower())(request, **kwargs)
        return self.get_process_renderer().show(request, **kwargs)


    def finalize(self, request, response):
        if self.get_success_url() and self.is_request_owner(request):
            form = self.get_form(self.get_form_class())
            if form.is_valid():
                return self.form_valid(form)

    def is_request_owner(self, request):
        return self.get_submit_name() in request.REQUEST

    def get_submit_name(self):
        return unicode(''.join((self.get_content_prefix(),
                                self.template_name_suffix)))

    def get_object(self):
        return self.object

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super(BasePublicForm, self).get_form_kwargs(*args, 
                                                               **kwargs)
        form_kwargs.update({'prefix':self.get_content_prefix()})
        return form_kwargs

    def get_form(self, form_class):
        form = super(BasePublicForm, self).get_form(form_class)
        form.submit_name = self.get_submit_name()
        return form


class BaseCreatePublicForm(BasePublicForm, CreateView):

    template_name_suffix = '_create'

    def get_object(self):
        pass


class BaseUpdatePublicForm(BasePublicForm, UpdateView):
    '''Update'''
    template_name_suffix = '_update'


class BaseDeletePublicForm(BasePublicForm, DeleteView):
    '''Delete'''
    template_name_suffix = '_delete'
    def get_form_class(self, *args, **kwargs):
        dummy_parent_form = getattr(self, 'form_class', Form)
        class DummyDeleteForm(dummy_parent_form and dummy_parent_form or Form):
            def __unicode__(self):
                return u''

        for k in DummyDeleteForm.base_fields:
            del DummyDeleteForm.base_fields[k]

        return DummyDeleteForm

    def get_form(self, form_class):
        form = form_class(**self.get_form_kwargs())
        form.submit_name = self.get_submit_name()
        return form
    
    def get_initial(self):
        return {}

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = FormView.get_form_kwargs.\
                        __get__(self, FormView)(*args, **kwargs)
        form_kwargs.update({'prefix':self.get_content_prefix()})
        return form_kwargs

    def form_valid(self, form):
        return self.delete(self.request)

CAPTCHA_PASSED_SESSION_KEY = 'captcha_passed'

class PublicFormCaptchaMixin(object):
    captcha_field_class = ReCaptchaFieldAjax
    
    @property
    def form_contains_errors(self):

        # if hasattr(self, 'sibling'):
        #     form = self.sibling.get_form(self.sibling.get_form_class())
        # else:
        #     form = 
        # # print 'fce', self.__class__, self, form.is_valid()
        return self.get_form(self.get_form_class()).is_valid()
    

    def is_captcha_required(self, request):
        if request.user.is_authenticated():
            return False

        if self.instance.enable_captcha_always:
            return True
        if self.instance.enable_captcha_once:
            return not request.session.get(CAPTCHA_PASSED_SESSION_KEY, False)

    def get_captcha_field_kwargs(self, request):
        kwargs = {'context':{}}
        formclass = self.get_form_class()
        kwargs['request'] = self.request
        preferred_lang = get_language_from_request(self.request)
        kwargs['attrs'] = {}
        kwargs['attrs']['lang'] = preferred_lang if\
                                        preferred_lang in RECAPTCHA_SUPPORTED_LANUAGES else\
                                        settings.LANGUAGE_CODE[:2]
        if hasattr(self, 'instance'):
            kwargs['context']['container_id'] = self.get_content_prefix()
        
        
        kwargs['context']['required_fields'] = []
        for fields_dict in (getattr(formclass, 'declared_fields', {}), 
                            getattr(formclass, 'base_fields', {})):
            for name, field in fields_dict.items():
                if field.required and not name in kwargs['context']['required_fields']:
                    kwargs['context']['required_fields'] += name,


        kwargs['context']['required_fields'] = mark_safe(json.dumps(kwargs['context']['required_fields']))
        
        kwargs['context']['form_errors'] = lambda:self.form_contains_errors
        return kwargs

    def get_captcha_field_class(self):
        return getattr(self, 'captcha_field_class', ReCaptchaFieldAjax)

    def append_captcha(self, formclass):
        captcha_field = self.get_captcha_field_class()\
                (**self.get_captcha_field_kwargs(self.request))
        formclass.base_fields[settings.PUBLIC_FORMS_CAPTCHA_FIELD_NAME] = captcha_field
        return formclass

class PublicFormAjaxMixin(object):
    html_types = ('text/html','application/xhtml+xml','application/xml')
    def is_accepts_html(self, request):
        for html_type in self.html_types:
            if html_type in request['Accept']:
                return True
        return False

    def is_ajax(self, request):
        return self.request.is_ajax() and self.is_accepts_html(request)

class PublicFormMediaMixin(object):
    def get_media(self):
        print 'gm0', self.__class__, self
        if not self.is_request_owner(self.request):
            self = self.get_process_renderer()
         
        form_media = self.get_form(self.get_form_class()).media
        _media = getattr(self, 'media', Media())
        _media.add_css(form_media._css)
        _media.add_js(form_media._js)
        print 'gm1'
        return _media

def get__get_form_class(public_formclass_renderer_class):
    def get_form_class(self):
        if not hasattr(self, '_formclass'):
            print 'gfc', self, self.__class__
            self._formclass = super(public_formclass_renderer_class, 
                            self).get_form_class()

            if self.is_captcha_required(self.request):
                self._formclass = self.append_captcha(self._formclass)

        return self._formclass
    
    return get_form_class.__get__(None, public_formclass_renderer_class)

# def get__get_form(public_formclass_renderer_class):
#     def get_form(self, form_class):
#         if not hasattr(self, '_form'):
#             self._form = super(public_formclass_renderer_class, 
#                             self).get_form(form_class)
#         return self._form
    
#     return get_form.__get__(None, public_formclass_renderer_class)



def get__process(public_form_renderer_class):
    def process(self, request, **kwargs):
        if not request.is_ajax():
            return super(public_form_renderer_class, 
                    self).process(request, **kwargs)
    
    return process.__get__(None, public_form_renderer_class)

def get__finalize(public_form_renderer_class):
    def finalize(self, request, response):
        if not request.is_ajax():
            return super(public_form_renderer_class,
                    self).finalize(request, response)
    
    return finalize.__get__(None, public_form_renderer_class)

class CreatePublicForm(PublicFormMediaMixin,
                       PublicFormAjaxMixin,
                       PublicFormCaptchaMixin,
                       BaseCreatePublicForm):
    '''Create'''

class UpdatePublicForm(PublicFormMediaMixin,
                       PublicFormAjaxMixin,
                       PublicFormCaptchaMixin,
                       BaseUpdatePublicForm):
    '''Update'''

class DeletePublicForm(PublicFormMediaMixin,
                       PublicFormAjaxMixin,
                       PublicFormCaptchaMixin,
                       BaseDeletePublicForm):
    '''Delete'''

for public_form in (CreatePublicForm, UpdatePublicForm, DeletePublicForm):
    # public_form.get_form = get__get_form(public_form)
    public_form.get_form_class = get__get_form_class(public_form)
    public_form.process = get__process(public_form)
    public_form.finalize = get__finalize(public_form)