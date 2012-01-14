from functools import wraps
from django.views.generic.edit import (CreateView,
                                       UpdateView,
                                       DeleteView,
                                       FormView,
                                       ModelFormMixin,
                                       TemplateResponseMixin)
from collections import OrderedDict
from copy import copy

from django.forms import Form, ModelForm, Media
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.template.response import TemplateResponse
from django.utils.translation import get_language_from_request
from django.utils.safestring import mark_safe
from django.utils import simplejson as json
from django.utils.translation import ugettext as _
from django.forms.models import inlineformset_factory
from django.db.models import ForeignKey

from captcha.fields import ReCaptchaFieldAjax
from captcha.client import RECAPTCHA_SUPPORTED_LANUAGES

from feincms.page.extensions.variative_renderer.renderers import (BaseRenderer,
                                                TemplateResponseRendererMixin)


from . import settings

#TODO: get_form caching


CAPTCHA_PASSED_SESSION_KEY = getattr(settings,
                                    'PUBLIC_FORMS_CAPTCHA_PASSED_SESSION_KEY',
                                    'captcha_passed')


class PublicFormMediaMixin(object):
    def get_media(self):
        if hasattr(self, '_presentation'):
            self = self._presentation
        form_media = self.get_form(self.get_form_class()).media
        media = getattr(self, 'media', Media())
        media.add_css(form_media._css)
        media.add_js(form_media._js)
        return media


class PublicFormAjaxMixin(object):
    def ajax_on_prepare(self, request, **kwargs):
        #short circuit to ajax response
        self.response_class = TemplateResponse
        self.on_prepare(request)
        return self.render(request, **kwargs)


class PublicFormCaptchaMixin(object):
    captcha_field_class = ReCaptchaFieldAjax
    
    @property
    def form_contains_errors(self):
        if not hasattr(self, '_form_contains_errors'):
            self._form_contains_errors = self.get_form(self.get_form_class()).is_valid()
        self._form_contains_errors            
    
    def is_captcha_required(self, request):
        if request.user.is_authenticated():
            return False

        if self.instance.enable_captcha_always:
            return True
        if self.instance.enable_captcha_once:
            return not request.session.get(CAPTCHA_PASSED_SESSION_KEY, False)

    def get_captcha_field_kwargs(self, request, formclass):
        kwargs = {'context':{}}
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
        return self.captcha_field_class

    def append_captcha(self, formclass):
        captcha_field = self.get_captcha_field_class()\
                (**self.get_captcha_field_kwargs(self.request, formclass))
        formclass.base_fields[settings.PUBLIC_FORMS_CAPTCHA_FIELD_NAME] = \
                                                                captcha_field
        return formclass

class PublicFormRelatedInlineFormsetMixin(object):
    default_inlineformset_factory_kwargs = getattr(settings,
                                'PUBLIC_FORMS_DEFAULT_FORMSET_FACTORY_KWARGS',
                                {'extra':2})
    @property
    def formset_factory(self):
        return inlineformset_factory
    
    def append_formset_validation(self, get_form):
        #appends additional validation for form.is_valid
        renderer = self
        @wraps(get_form)
        def wrapped(*args, **kwargs):
            form = get_form(*args, **kwargs)
            form.is_valid = renderer.append_is_formset_valid(form.is_valid)
            
            return form
        
        return wrapped

    def append_is_formset_valid(self, is_valid):
        #actual additional validation for form.is_valid
        renderer = self
        @wraps(is_valid)
        def wrapped(*args, **kwargs):
            form_is_valid = is_valid(*args, **kwargs)
            self.object = self.get_form().instance
            def now_get_object_must_return_instance_in_any_case(self):
                return self.object
            renderer.get_object = now_get_object_must_return_instance_in_any_case.\
                                  __get__(renderer, renderer.__class__)

            for formset in renderer.get_formsets().values():
                form_is_valid = form_is_valid and formset.is_valid()


            return form_is_valid
        
        return wrapped
    
    def formset_valid_post_save(self):
        if not self.get_success_url():
            #recreate formset since old one contains posted 
            #data (together with delete checkboxes and so forth)
            #we need actial instance data instead
            orig_get_formset_kwargs = self.get_formset_kwargs
            def get_formset_kwargs(self, **extra):
                kwargs = orig_get_formset_kwargs(**extra)
                'data' in kwargs and kwargs.pop('data')
                'files' in kwargs and kwargs.pop('files')
                return kwargs

            self.get_formset_kwargs = get_formset_kwargs.__get__(self,
                                                        self.__class__)

            self._cached_get_formsets_result = OrderedDict(self.iter_formsets())

    def append_formset_valid(self, form_valid):
        #action for self.form_valid extended with formsets.save()
        renderer = self
        @wraps(form_valid)
        def wrapped(*args, **kwargs):
            ret = form_valid(*args, **kwargs)
            for formset in renderer.get_formsets().values():
                formset.save()
            self.formset_valid_post_save()
            return ret
            
        
        return wrapped

    def iter_formsets_classes_args(self, get_formset_class_args):
        for args in get_formset_class_args:
            yield [self.get_form_class(), self.model]+list(args)
    
    def get_formset_title(self, through):
        if not through._meta.auto_created:
            return u'%s'%through._meta.verbose_name_plural
        elif not through._meta.auto_created is self.model:
            return u'%s'%through._meta.auto_created._meta.verbose_name_plural
        else:
            for field in through._meta.fields:
                if isinstance(field, ForeignKey) \
                    and (field.related.parent_model!=self.model):
                        return u'%s'%field.related.parent_model._meta.\
                                                verbose_name_plural

    def iter_formsets(self):
        for inline, kwargs in getattr(self, 'inlines', ()):
            kw = copy(self.default_inlineformset_factory_kwargs)
            kw.update(kwargs)
            self.add_inline(inline, **kw)

        for args in self.iter_formsets_classes_args(getattr(self,
                                                    'get_formset_class_args',
                                                    ())):
            #get_formset_class must be called before get_formset_title,
            #but returned value must be reversed for dict() casting
            formset = self.get_formset_class(*args)(**self.get_formset_kwargs())
            title = self.get_formset_title(args[2])
            
            yield title, formset
        
    def get_formsets(self):
        return OrderedDict(self.iter_formsets())

    def add_inline(self, through, **inlineformset_factory_kwargs):
        if not hasattr(self, 'get_formset_class_args'):
            self.get_formset_class_args = []
        
        get_formset_class_args = (through,
                                  inlineformset_factory_kwargs \
                              if inlineformset_factory_kwargs \
                              else self.default_inlineformset_factory_kwargs)

        if not get_formset_class_args in self.get_formset_class_args:
            self.get_formset_class_args += get_formset_class_args,

    def get_formset_class(self, form_class, parent, through, factory_kwargs):
        return self.formset_factory(parent,
                                          through,
                                          form_class,
                                          **factory_kwargs)

    def get_formset_kwargs(self, **extra):
        kwargs = {'instance':self.get_object(),
                  'prefix':self.get_content_prefix(),}
        
        self.request.POST and kwargs.update({'data':self.request.POST})
        self.request.FILES and kwargs.update({'files':self.request.FILES})
        kwargs.update(extra)
        return kwargs

    def get_formset(self, formset_class, **kwargs):
        return formset_class(**self.get_formset_kwargs(**kwargs))

class BasePublicForm(BaseRenderer,
                     TemplateResponseRendererMixin,
                     TemplateResponseMixin,
                     PublicFormCaptchaMixin,
                     PublicFormAjaxMixin,
                     PublicFormMediaMixin,
                     PublicFormRelatedInlineFormsetMixin):

    base_to_default = False
    form_class_modifiers = (('is_captcha_required', 'append_captcha'),)
    
    def is_request_owner(self, request):
        return self.get_submit_name() in request.REQUEST

    def get_submit_name(self):
        if not hasattr(self, '_submit_name'):
            self._submit_name = unicode(''.join((self.get_content_prefix(),
                                self.template_name_suffix)))
        return self._submit_name

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

    def get_context_data(self, **kwargs):
        context = super(BasePublicForm, self).get_context_data(**kwargs)
        context['action_title'] = _(self.get_title())
        context['public_form_content'] = lambda:self.instance
        context['formsets'] = self.get_formsets()
        return context

    def prepare_page(self, request):
        if hasattr(request, '_feincms_page'):
            self.page = request._feincms_page
            self.page.contains_forms = True

    def on_prepare(self, request, **kwargs):
        self.object = self.instance.content_object
        self.model = self.instance.content_type.model_class()
        self.prepare_page(request)
        self.get_form_class = self.append_modifiers(self.get_form_class,
                                    self.form_class_modifiers)
        
        self.get_form = self.append_formset_validation(self.get_form)
        self.form_valid = self.append_formset_valid(self.form_valid)
        
        self.get_form_class = self.cached_method(self.get_form_class)
        self.get_form = self.cached_method(self.get_form)
        self.get_formsets = self.cached_method(self.get_formsets)

    def append_modifiers(self, wrapped, modifiers):
        @wraps(wrapped)
        def wrapper(self, *args, **kwargs):
            result = wrapped(*args, **kwargs)
            for condition_name, modifier_name in modifiers:
                condition = getattr(self, condition_name)
                modifier = getattr(self, modifier_name)
                if condition(self.request):
                    result = modifier(result)
            return result
        return wrapper.__get__(self, self.__class__)

    def cached_method(self, wrapped):
        instance = self
        cache_name = '_cached_%s_result'%wrapped.func_name
        @wraps(wrapped)
        def wrapper(self, *args, **kwargs):
            if not hasattr(instance, cache_name):
                setattr(instance, cache_name, wrapped(*args, **kwargs))
            return getattr(instance, cache_name)
        return wrapper.__get__(self, self.__class__)

    def copy_members(self, member_names, source):
        for name in member_names:
            if hasattr(source, name):
                setattr(self, name, getattr(source, name))

class BasePresentationPublicForm(BasePublicForm,
                                 SingleObjectTemplateResponseMixin,
                                 ModelFormMixin):
    def render(self, request, *args, **kwargs):
        form = self.get_form(self.get_form_class())
        return self.render_to_response(self.get_context_data(form=form))

    def get_form_kwargs(self):
        ret = super(BasePresentationPublicForm, self).get_form_kwargs()
        'data' in ret and ret.pop('data')
        'files' in ret and ret.pop('files')
        return ret

    def get_formset_kwargs(self, **extra):
        ret = super(BasePresentationPublicForm, self).get_formset_kwargs()
        'data' in ret and ret.pop('data')
        'files' in ret and ret.pop('files')
        return ret

    def on_response(self, request, response):
        pass


class BaseModificationPublicForm(BasePublicForm,
                                 SingleObjectTemplateResponseMixin,
                                 ModelFormMixin):
    success_action = False
    def get_success_url(self):
        if getattr(self, 'success_action', False):
            if getattr(self, 'success_url', None) is None:
                self.success_url = self.page._cached_url
            return self.success_url and self.success_url \
                    or self.object.get_absolute_url()
        else:
            return None
                
    def on_response(self, request, response):
        if self.get_success_url():
            form = self.get_form(self.get_form_class())
            if form.is_valid():
                return self.form_valid(form)

    def render(self, request, **kwargs):
        form = self.get_form(self.get_form_class())
        getattr(self, request.method.lower())(request, **kwargs)
        return self.render_to_response(self.get_context_data(form=form))


class PublicFormRequestDispatcher(object):
    presentation_class = BasePresentationPublicForm
    copy_members_to_presentation = ('instance',
                                    'owner',
                                    'template_name_suffix',
                                    'form_class',
                                    'media',
                                    'inlines',
                                    'get_formset_class_args')

    @property
    def presentation(self):
        if not hasattr(self, '_presentation'):
            presentation = self.presentation_class(*self._init_args,
                                                   **self._init_kwargs)
            
            presentation.copy_members(self.copy_members_to_presentation,
                                      self)
            
            presentation.get_form_class = presentation.\
                                append_modifiers(presentation.get_form_class,
                                        presentation.form_class_modifiers)
            for method in (presentation.get_form_class,
                           presentation.get_form,
                           presentation.get_formsets):
                method = presentation.cached_method(method) 
            
            presentation.request = self.request
            self._presentation = presentation
        return self._presentation

    def dispatch_method(self, method_name, request):
        self.request = request
        if self.is_request_owner(request):
            if request.is_ajax():
                return getattr(self, 'ajax_%s'%method_name)
            else:
                return getattr(self, method_name)
        else:
            return getattr(self.presentation, method_name)
        

    def __call__(self, request, *args, **kwargs):
        return unicode(self.dispatch_method('render',
                                        request)(request, *args, **kwargs))

    def process(self, request, **kwargs):
        return self.dispatch_method('on_prepare', request)(request, **kwargs)

    def finalize(self, request, response):
        return self.dispatch_method('on_response', request)(request, response)
        

class BaseCreatePublicForm(BaseModificationPublicForm, CreateView):
    template_name_suffix = '_create'
    def get_object(self):
        pass
    
    def form_valid(self, form):
        ret = super(BaseCreatePublicForm, self).form_valid(form)
        form.data = {}
        form.instance = None
        form.files = {}
        return ret

    def formset_valid_post_save(self):
        if not self.get_success_url():
            #recreate formset since old one contains posted 
            #data (together with delete checkboxes and so forth)
            #we need actial instance data instead
            orig_get_formset_kwargs = self.get_formset_kwargs
            def get_formset_kwargs(self, **extra):
                kwargs = orig_get_formset_kwargs(**extra)
                'data' in kwargs and kwargs.pop('data')
                'files' in kwargs and kwargs.pop('files')
                'instance' in kwargs and kwargs.pop('instance')
                return kwargs

            self.get_formset_kwargs = get_formset_kwargs.__get__(self,
                                                        self.__class__)

            self._cached_get_formsets_result = \
                                    OrderedDict(self.iter_formsets())

class BaseUpdatePublicForm(BaseModificationPublicForm, UpdateView):
    '''Update'''
    template_name_suffix = '_update'


class BaseDeletePublicForm(BaseModificationPublicForm, DeleteView):
    '''Delete'''
    template_name_suffix = '_delete'
    def get_form_class(self, *args, **kwargs):
        dummy_parent_form = getattr(self, 'form_class', Form)
        class DummyDeleteForm(dummy_parent_form and dummy_parent_form or Form):
            class Meta:
                model = self.model
            def __unicode__(self):
                return u''

        for k in DummyDeleteForm.base_fields:
            del DummyDeleteForm.base_fields[k]


        return DummyDeleteForm

    def get_form(self, form_class):
        form = form_class(**self.get_form_kwargs())
        form.instance = self.get_object()
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

    def iter_formsets_classes_args(self, get_formset_class_args):
        for args in get_formset_class_args:
            yield [ModelForm, self.model]+list(args)

class BaseDeletePublicFormPresentation(BasePresentationPublicForm):
    get_form_class = BaseDeletePublicForm.get_form_class.__func__
    get_form = BaseDeletePublicForm.get_form.__func__
    get_form_kwargs = BaseDeletePublicForm.get_form_kwargs.__func__
    iter_formsets_classes_args = \
                BaseDeletePublicForm.iter_formsets_classes_args.__func__

class BaseCreatePublicFormPresentation(BasePresentationPublicForm):
    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super(BaseCreatePublicFormPresentation,
                                    self).get_form_kwargs(*args, **kwargs)
        'instance' in kwargs and kwargs.pop('instance')
        return kwargs

    def get_formset_kwargs(self, *args, **kwargs):
        kwargs = super(BaseCreatePublicFormPresentation,
                                    self).get_formset_kwargs(*args, **kwargs)
        'instance' in kwargs and kwargs.pop('instance')

        return kwargs

class CreatePublicForm(PublicFormRequestDispatcher, BaseCreatePublicForm):
    presentation_class = BaseCreatePublicFormPresentation
    '''Create'''
    pass


class UpdatePublicForm(PublicFormRequestDispatcher, BaseUpdatePublicForm):
    '''Update'''
    pass


class DeletePublicForm(PublicFormRequestDispatcher, BaseDeletePublicForm):
    '''Delete'''
    presentation_class = BaseDeletePublicFormPresentation
    