import os
from random import choice
from importlib import import_module
from inspect import getmembers

from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from django.test.client import Client
from django.test.client import RequestFactory
from django.contrib.sites.models import Site

from feincms.module.page.models import Page

from .models import PublicForm
from .renderers import BasePublicForm, CreatePublicForm
from . import settings

def path_represented_object(path):
    obj_module, obj_name = path.rsplit('.', 1)
    if not obj_module or not obj_name:
        raise ValueError('%s is not a valid module path'%path)
    return getattr(import_module(obj_module), obj_name)

def module_content_types(module, content_type):
    '''returns all subclasses of content type registered for module'''
    for concrete_model in module._feincms_content_types:
        if issubclass(concrete_model, content_type):
            yield concrete_model

def module_content_type(*args):
    for model in module_content_types(*args):
        return model

class RequirementsTest(TestCase):
    def test_variative_importable(self):
        from feincms.page.extensions import variative_renderer

class PublicFormsTestCase(TestCase):
    template = 'content/sites/site_create.html'
    template_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 
                                     'templates', 
                                     template)
    template_dir = os.path.abspath(os.path.dirname(template_path))
    curdir = os.path.abspath(os.path.dirname(__file__))


    def setUp(self):
        self.setup_page()
        self.client = Client()
        self.setup_request_factory()

    def tearDown(self):
        if os.path.exists(self.template_path):
            os.remove(self.template_path)

    def setup_request_factory(self):
            self.factory = RequestFactory()
            orig_get = self.factory.get
            orig_post = self.factory.post
            def append_middlewares(request):
                for middleware in settings.MIDDLEWARE_CLASSES:
                    if isinstance(middleware, basestring):
                        middleware = path_represented_object(middleware)
                    getattr(middleware(), 'process_request',  lambda x:x)(request)
                return request
            
            def get(self, *args, **kwargs):
                return append_middlewares(orig_get(*args, **kwargs))

            def post(self, *args, **kwargs):
                return append_middlewares(orig_post(*args, **kwargs))

            self.factory.get = get.__get__(self.factory, RequestFactory)
            self.factory.post = post.__get__(self.factory, RequestFactory)
    def setup_page(self, title='test22'):
        Page.register_templates({
                'title': 'Testing template',
                'path': self.template,
                'regions': (
                    ('first_col', 'First column'),
                    ('second_col', 'Second column'),
                    ('third_col', 'Third column'),
                    ),
                })

        page_kwargs = {'rght': 2, 'level': 0, 
                       'title': title,
                       'slug':''.join([choice('abcdfghjk') for i in xrange(50)]),
                       'redirect_to': u'', 
                       'override_url':'',
                       'parent_id': None, 
                       'lft': 1, 
                       'template_key': self.template,
                       'tree_id': 1, 'active': True, 
                       'in_navigation': True, 'slug': title,}

        
        for p in Page.objects.all():
            try:
                p.delete()
            except:
                pass

        self.page = Page(**page_kwargs)
        self.page.save()
        return self.page
    
    def setup_template(self, template):
        if not os.path.exists(self.template_dir):
            os.makedirs(self.template_dir)
    
class BasePublicFormsTest(PublicFormsTestCase):
    '''Create'''
    pass

class CreatePublicFormsTest(PublicFormsTestCase):
    def test_get_object_returns_none(self):
        pf_kwargs = {
                     'region':'first_col',
                     'enable_captcha':False,
                     'enable_ajax':False,
                     'object_id':None,
                     'content_type':ContentType.objects.get_for_model(Site),
                     'variation':u'CreatePublicForm',
                     'parent':self.page,
                     }
        pf_ct = module_content_type(Page, PublicForm)
        pf = pf_ct(**pf_kwargs)
        self.assert_(pf.render.get_object() is None)
    def test_renderer_for_not_request_owner_is_form_processing_renderer(self):
        pf_kwargs = {
                     'region':'first_col',
                     'enable_captcha':False,
                     'enable_ajax':False,
                     'object_id':None,
                     'content_type':ContentType.objects.get_for_model(Site),
                     'variation':u'CreatePublicForm',
                     'parent':self.page,
                     }
        pf_ct = module_content_type(Page, PublicForm)
        pf = pf_ct(**pf_kwargs)
        pf.save()

        request = self.factory.get(self.page._cached_url)
        pf.process(request)
        self.assert_(issubclass(dict(getmembers(pf.render.render))['im_class'],
                     BasePublicForm.process_view))

    def test_renderer_for_request_owner_is_creation_renderer(self):
        pf_kwargs = {
                     'region':'first_col',
                     'enable_captcha':False,
                     'enable_ajax':False,
                     'object_id':None,
                     'content_type':ContentType.objects.get_for_model(Site),
                     'variation':u'CreatePublicForm',
                     'parent':self.page,
                     }
        pf_ct = module_content_type(Page, PublicForm)
        pf = pf_ct(**pf_kwargs)
        pf.save()

        request = self.factory.get(self.page._cached_url)
        def is_request_owner(self, request):
            return True
        pf.is_request_owner = is_request_owner.__get__(pf, pf.__class__)

        pf.process(request)
        self.assert_(issubclass(dict(getmembers(pf.render.render))['im_class'],
                     CreatePublicForm))
    
    def test_is_request_owner_returns_true_for_correct_prefix(self):
        pf_kwargs = {
                     'region':'first_col',
                     'enable_captcha':False,
                     'enable_ajax':False,
                     'object_id':None,
                     'content_type':ContentType.objects.get_for_model(Site),
                     'variation':u'CreatePublicForm',
                     'parent':self.page,
                     'ordering':0
                     }
        pf_ct = module_content_type(Page, PublicForm)
        pf = pf_ct(**pf_kwargs)
        pf.save()
        request = self.factory.get('%s?test22_first_col_0_create'%self.page._cached_url)
        self.assert_(pf.render.is_request_owner(request))

        request = self.factory.get(self.page._cached_url, data={'test22_first_col_0_create':True})
        self.assert_(pf.render.is_request_owner(request))

class UpdatePublicFormsTest(PublicFormsTestCase):
    def test_is_request_owner_returns_true_for_correct_prefix(self):
        pf_kwargs = {
                     'region':'first_col',
                     'enable_captcha':False,
                     'enable_ajax':False,
                     'object_id':None,
                     'content_type':ContentType.objects.get_for_model(Site),
                     'variation':u'UpdatePublicForm',
                     'parent':self.page,
                     'ordering':0
                     }
        pf_ct = module_content_type(Page, PublicForm)
        pf = pf_ct(**pf_kwargs)
        pf.save()
        request = self.factory.get('%s?test22_first_col_0_update'%self.page._cached_url)
        self.assert_(pf.render.is_request_owner(request))

        request = self.factory.get(self.page._cached_url, 
                                   data={'test22_first_col_0_update':True})
        self.assert_(pf.render.is_request_owner(request))

class DeletePublicFormsTest(PublicFormsTestCase):
    def test_is_request_owner_returns_true_for_correct_prefix(self):
        pf_kwargs = {
                     'region':'first_col',
                     'enable_captcha':False,
                     'enable_ajax':False,
                     'object_id':None,
                     'content_type':ContentType.objects.get_for_model(Site),
                     'variation':u'DeletePublicForm',
                     'parent':self.page,
                     'ordering':0
                     }
        pf_ct = module_content_type(Page, PublicForm)
        pf = pf_ct(**pf_kwargs)
        pf.save()
        request = self.factory.get('%s?test22_first_col_0_delete'%self.page._cached_url)
        self.assert_(pf.render.is_request_owner(request))

        request = self.factory.get(self.page._cached_url, 
                                   data={'test22_first_col_0_delete':True})
        self.assert_(pf.render.is_request_owner(request))