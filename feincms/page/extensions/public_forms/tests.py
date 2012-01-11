import os
from random import choice
from importlib import import_module
from inspect import getmembers
from tempfile import mkstemp
import subprocess

import imp

from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from django.test.client import Client
from django.test.client import RequestFactory
from django.contrib.sites.models import Site
from django.contrib.auth import authenticate, login
from django.forms import Form, ModelForm, Media

from captcha.fields import ReCaptchaFieldAjax

from feincms.module.page.models import Page

from feincms.views.cbv.views import Handler

from feincms.page.extensions.variative_renderer.renderers import RendererSelectionWrapper

from .models import PublicForm
from .renderers import (BasePublicForm, 
                        CreatePublicForm, 
                        UpdatePublicForm, 
                        DeletePublicForm,
                        CAPTCHA_PASSED_SESSION_KEY)
from . import settings


#pf - public form
#ct - content type

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

def prettyHTML(html):
    try:
        from BeautifulSoup import BeautifulSoup as bs
    except ImportError, e:
        print e
        return html

    soup = bs(html)
    return soup.prettify()

def show_in_browser(html):
    fd, tmpfile = mkstemp(suffix='.html')
    os.fdopen(fd).close()
    with open(tmpfile, 'w') as temp:
        temp.write(html)
    subprocess.Popen('xdg-open file://%s'%tmpfile, shell=True)

class RequirementsTest(TestCase):
    def test_variative_importable(self):
        from feincms.page.extensions import variative_renderer

PACKAGE_DIR = os.path.abspath(os.path.dirname(
                import_module('feincms.page.extensions.public_forms').\
                __file__))
TEMPLATES_DIR = os.path.join(PACKAGE_DIR, 'templates')

class FeincmsPageTestCase(TestCase):
    templates_dir = TEMPLATES_DIR
    page_template_name = 'tespage.html'
    page_template_text = """{%spaceless%}{% load feincms_tags %}
        <div class="page-content">{% feincms_render_region feincms_page "first_col" request %}</div>
        <div class="page-content">{% feincms_render_region feincms_page "second_col" request %}</div>
        <div class="page-content">{% feincms_render_region feincms_page "third_col" request %}</div>{%endspaceless%}"""

    def setUp(self):
        self.setup_page()
        self.client = Client()
        self.setup_request_factory()

    def tearDown(self):
        for template_path in getattr(self, 'template_pathes', []):
            if os.path.exists(template_path):
                os.remove(template_path)
        self.template_pathes = []

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
    
    def setup_template(self, template_path, template_text):
        template_path = os.path.join(self.templates_dir, template_path)
        template_dir = os.path.abspath(os.path.dirname(template_path))
        if os.path.exists(template_path):
            raise IOError('Template "%s" exists'%template_path)

        if not os.path.exists(template_dir):
            os.makedirs(template_dir)
        
        with open(template_path, 'w') as template_file:
            template_file.write(template_text)
        
        if not hasattr(self, 'template_pathes'):
            self.template_pathes = []

        self.template_pathes += template_path,

    def setup_page(self, title='test22'):
        for p in Page.objects.all():
            try:
                p.delete()
            except:
                pass

        self.setup_template(self.page_template_name, 
                            self.page_template_text)
        Page.register_templates({
                'title': 'Testing template',
                'path': self.page_template_name,
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
                       'template_key': self.page_template_name,
                       'tree_id': 1, 'active': True, 
                       'in_navigation': True, 'slug': title,}

        self.page = Page(**page_kwargs)
        self.page.save()
        return self.page


class CreatePublicFormsTest(FeincmsPageTestCase):
    def test_get_object_returns_none(self):
        pf_kwargs = {
                     'region':'first_col',
                     'enable_captcha_once':False,
                     'enable_captcha_always':False,
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
                     'enable_captcha_once':False,
                     'enable_captcha_always':False,
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
                     'enable_captcha_once':False,
                     'enable_captcha_always':False,
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
                     'enable_captcha_once':False,
                     'enable_captcha_always':False,
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

    def test_submit_name(self):
        pf_kwargs = {
                     'region':'first_col',
                     'enable_captcha_once':False,
                     'enable_captcha_always':False,
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
        self.setup_template('content/sites/site_create.html',
                            """<form method='POST'>{{form}}<input type="submit" name="{{form.submit_name}}"/></form>"""
                            )

        response = self.client.get(self.page._cached_url)
        self.assert_("""<input type="submit" name="test22_first_col_0_create"/>""" in response.content)


    def test_create_with_success_action_redirects(self):
        class TestRenderer(CreatePublicForm):
             success_action = True
        pf_kwargs = {
                 'region':'first_col',
                 'enable_captcha_once':False,
                 'enable_captcha_always':False,
                 'enable_ajax':False,
                 'object_id':None,
                 'content_type':ContentType.objects.get_for_model(Site),
                 'variation':'TestRenderer',
                 'parent':self.page,
                 'ordering':0
                     }
        create_pf_ct = module_content_type(Page, PublicForm)
        orig_render = create_pf_ct.render
        try:
            create_pf_ct.render = RendererSelectionWrapper([TestRenderer,])
            create_pf = create_pf_ct(**pf_kwargs)
            create_pf.save()
            self.setup_template('content/sites/site_create.html',
                                """<form method='POST'>{{form}}<input type="submit" name="{{form.submit_name}}"/></form>"""
                                )

            response = self.client.post(self.page._cached_url,
                                        data={'test22_first_col_0-domain':'',
                                              'test22_first_col_0-name':'',
                                              'test22_first_col_0_create':'submit'})
            
            self.assert_('<ul class="errorlist"><li>This field is required.</li></ul>' \
                           in response.content)
            response = self.client.post(self.page._cached_url,
                                        data={'test22_first_col_0-domain':'a',
                                              'test22_first_col_0-name':'b',
                                              'test22_first_col_0_create':'submit'})
            self.assert_(response.status_code == 302)

            self.assert_(self.page._cached_url in response['Location'])
        finally:
            create_pf_ct.render = orig_render
    pass
        

class UpdatePublicFormsTest(FeincmsPageTestCase):
    def test_is_request_owner_returns_true_for_correct_prefix(self):
        pf_kwargs = {
                     'region':'first_col',
                     'enable_captcha_once':False,
                     'enable_captcha_always':False,
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

    def test_renderer_for_not_request_owner_is_form_processing_renderer(self):
        pf_kwargs = {
                     'region':'first_col',
                     'enable_captcha_once':False,
                     'enable_captcha_always':False,
                     'enable_ajax':False,
                     'object_id':None,
                     'content_type':ContentType.objects.get_for_model(Site),
                     'variation':u'UpdatePublicForm',
                     'parent':self.page,
                     }
        pf_ct = module_content_type(Page, PublicForm)
        pf = pf_ct(**pf_kwargs)
        pf.save()

        request = self.factory.get(self.page._cached_url)
        pf.process(request)
        self.assert_(issubclass(dict(getmembers(pf.render.render))['im_class'],
                     BasePublicForm.process_view))

    def test_renderer_for_request_owner_is_update_renderer(self):
            pf_kwargs = {
                         'region':'first_col',
                         'enable_captcha_once':False,
                         'enable_captcha_always':False,
                         'enable_ajax':False,
                         'object_id':None,
                         'content_type':ContentType.objects.get_for_model(Site),
                         'variation':u'UpdatePublicForm',
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
                         UpdatePublicForm))

    def test_is_request_owner_returns_true_for_correct_prefix(self):
        pf_kwargs = {
                     'region':'first_col',
                     'enable_captcha_once':False,
                     'enable_captcha_always':False,
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

    def test_submit_name(self):
        pf_kwargs = {
                     'region':'first_col',
                     'enable_captcha_once':False,
                     'enable_captcha_always':False,
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
        self.setup_template('content/sites/site_update.html',
                            """<form method='POST'>{{form}}<input type="submit" name="{{form.submit_name}}"/></form>"""
                            )

        response = self.client.get(self.page._cached_url)
        self.assert_("""<input type="submit" name="test22_first_col_0_update"/>""" in response.content)

    def test_update_with_success_action_redirects(self):
        class TestRenderer(UpdatePublicForm):
             success_action = True
        pf_kwargs = {
                 'region':'first_col',
                 'enable_captcha_once':False,
                 'enable_captcha_always':False,
                 'enable_ajax':False,
                 'object_id':1,
                 'content_type':ContentType.objects.get_for_model(Site),
                 'variation':'TestRenderer',
                 'parent':self.page,
                 'ordering':0
                     }
        update_pf_ct = module_content_type(Page, PublicForm)
        orig_render = update_pf_ct.render
        try:
            update_pf_ct.render = RendererSelectionWrapper([TestRenderer,])
            update_pf = update_pf_ct(**pf_kwargs)
            update_pf.save()
            self.setup_template('content/sites/site_update.html',
                                """<form method='POST'>{{form}}<input type="submit" name="{{form.submit_name}}"/></form>"""
                                )

            response = self.client.post(self.page._cached_url,
                                        data={'test22_first_col_0-domain':'',
                                              'test22_first_col_0-name':'',
                                              'test22_first_col_0_update':'submit'})
            
            self.assert_('<ul class="errorlist"><li>This field is required.</li></ul>' \
                           in response.content)
            response = self.client.post(self.page._cached_url,
                                        data={'test22_first_col_0-domain':'a',
                                              'test22_first_col_0-name':'b',
                                              'test22_first_col_0_update':'submit'})
            self.assert_(response.status_code == 302)

            self.assert_(self.page._cached_url in response['Location'])
        finally:
            update_pf_ct.render = orig_render

class DeletePublicFormsTest(FeincmsPageTestCase):
    def test_is_request_owner_returns_true_for_correct_prefix(self):
        pf_kwargs = {
                     'region':'first_col',
                     'enable_captcha_once':False,
                     'enable_captcha_always':False,
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
    def test_renderer_for_not_request_owner_is_form_processing_renderer(self):
        pf_kwargs = {
                     'region':'first_col',
                     'enable_captcha_once':False,
                     'enable_captcha_always':False,
                     'enable_ajax':False,
                     'object_id':None,
                     'content_type':ContentType.objects.get_for_model(Site),
                     'variation':u'UpdatePublicForm',
                     'parent':self.page,
                     }
        pf_ct = module_content_type(Page, PublicForm)
        pf = pf_ct(**pf_kwargs)
        pf.save()

        request = self.factory.get(self.page._cached_url)
        pf.process(request)
        self.assert_(issubclass(dict(getmembers(pf.render.render))['im_class'],
                     BasePublicForm.process_view))

    def test_renderer_for_request_owner_is_update_renderer(self):
            pf_kwargs = {
                         'region':'first_col',
                         'enable_captcha_once':False,
                         'enable_captcha_always':False,
                         'enable_ajax':False,
                         'object_id':None,
                         'content_type':ContentType.objects.get_for_model(Site),
                         'variation':u'DeletePublicForm',
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
                         DeletePublicForm))

    def test_is_request_owner_returns_true_for_correct_prefix(self):
        pf_kwargs = {
                     'region':'first_col',
                     'enable_captcha_once':False,
                     'enable_captcha_always':False,
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

    def test_submit_name(self):     
        pf_kwargs = {
                     'region':'first_col',
                     'enable_captcha_once':False,
                     'enable_captcha_always':False,
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
        self.setup_template('content/sites/site_delete.html',
                            """<form method='POST'>{{form}}<input type="submit" name="{{form.submit_name}}"/></form>"""
                            )

        response = self.client.get(self.page._cached_url)
        self.assert_("""<input type="submit" name="test22_first_col_0_delete"/>""" in response.content)

    def test_delete_with_success_action_redirects(self):
        class TestRenderer(DeletePublicForm):
             success_action = True
        
        pf_kwargs = {
                 'region':'first_col',
                 'enable_captcha_once':False,
                 'enable_captcha_always':False,
                 'enable_ajax':False,
                 'object_id':1,
                 'content_type':ContentType.objects.get_for_model(Site),
                 'variation':'TestRenderer',
                 'parent':self.page,
                 'ordering':0
                     }
        
        delete_pf_ct = module_content_type(Page, PublicForm)
        orig_render = delete_pf_ct.render
        try:
            delete_pf_ct.render = RendererSelectionWrapper([TestRenderer,])
            delete_pf = delete_pf_ct(**pf_kwargs)
            delete_pf.save()
            self.setup_template('content/sites/site_delete.html',
                                """<form method='POST'>{{form}}<input type="submit" name="{{form.submit_name}}"/></form>"""
                                )

            response = self.client.post(self.page._cached_url,
                                        data={'test22_first_col_0_delete':'submit'})
            self.assert_(response.status_code == 302)

            self.assert_(self.page._cached_url in response['Location'])
        finally:
            delete_pf_ct.render = orig_render


class CRUDTest(FeincmsPageTestCase):
    def setup_crud_page(self):
        self.site_content_type = ContentType.objects.\
                                 get_for_model(Site)
        
        self.create_pf_kwargs = {
                 'region':'first_col',
                 'enable_captcha_once':False,
                 'enable_captcha_always':False,
                 'enable_ajax':False,
                 'object_id':None,
                 'content_type':self.site_content_type,
                 'variation':'CreatePublicForm',
                 'parent':self.page,
                 'ordering':0}

        self.update_pf_kwargs = {
                 'region':'second_col',
                 'enable_captcha_once':False,
                 'enable_captcha_always':False,
                 'enable_ajax':False,
                 'object_id':1,
                 'content_type':self.site_content_type,
                 'variation':'UpdatePublicForm',
                 'parent':self.page,
                 'ordering':0}
                 
        self.delete_pf_kwargs = {
                 'region':'third_col',
                 'enable_captcha_once':False,
                 'enable_captcha_always':False,
                 'enable_ajax':False,
                 'object_id':1,
                 'content_type':self.site_content_type,
                 'variation':'DeletePublicForm',
                 'parent':self.page,
                 'ordering':0}
                                          
        self.pf_ct = module_content_type(Page, PublicForm)
        self.create_pf_ct = self.pf_ct(**self.create_pf_kwargs)
        self.create_pf_ct.save()

        self.update_pf_ct = self.pf_ct(**self.update_pf_kwargs)
        self.update_pf_ct.save()

        self.delete_pf_ct = self.pf_ct(**self.delete_pf_kwargs)
        self.delete_pf_ct.save()
        self.create_templates()
    
    def tearDown(self):
        if hasattr(self, 'orig_render') and hasattr(self, 'pf_ct'):
            self.pf_ct.render = self.orig_render

        super(CRUDTest, self).tearDown()

class MultiformCRUDTestMixin(object):
    def test_successful_create(self):
        self.setup_crud_page()
        sites_n = Site.objects.all().count()
        response = self.client.post(self.page._cached_url,
                            data={'test22_first_col_0-domain':'a',
                                  'test22_first_col_0-name':'b',
                                  'test22_first_col_0_create':'submit'})
        self.assert_('errorlist' not in response.content)
        self.assert_(Site.objects.all().count() == (sites_n+1))


    def test_successful_create_with_success_action(self):
        class TestRenderer(CreatePublicForm):
             success_action = True
        
        pf_ct = module_content_type(Page, PublicForm)
        self.orig_render = pf_ct.render
        pf_ct.render = RendererSelectionWrapper([TestRenderer]+pf_ct.renderer_choices)
        self.setup_crud_page()


        self.create_pf_ct.variation = 'TestRenderer'
        self.create_pf_ct.save()
        

        sites_n = Site.objects.all().count()
        response = self.client.post(self.page._cached_url,
                            data={'test22_first_col_0-domain':'a',
                                  'test22_first_col_0-name':'b',
                                  'test22_first_col_0_create':'submit'})
        self.assert_(response.status_code == 302)
        self.assert_(self.page._cached_url in response['Location'])
        self.assert_(Site.objects.all().count() == (sites_n+1))

    def test_unsuccessful_create_with_success_action(self):
        class TestRenderer(CreatePublicForm):
             success_action = True
        
        pf_ct = module_content_type(Page, PublicForm)
        self.orig_render = pf_ct.render
        pf_ct.render = RendererSelectionWrapper([TestRenderer]+pf_ct.renderer_choices)
        self.setup_crud_page()


        self.create_pf_ct.variation = 'TestRenderer'
        self.create_pf_ct.save()
        

        sites_n = Site.objects.all().count()
        response = self.client.post(self.page._cached_url,
                            data={'test22_first_col_0-domain':'',
                                  'test22_first_col_0-name':'b',
                                  'test22_first_col_0_create':'submit'})
        self.assert_(response.status_code == 200)
        self.assert_('errorlist' in response.content)
        self.assert_(Site.objects.all().count() == sites_n)

    def test_successful_update_with_success_action(self):
        class TestRenderer(UpdatePublicForm):
             success_action = True
        
        pf_ct = module_content_type(Page, PublicForm)
        self.orig_render = pf_ct.render
        pf_ct.render = RendererSelectionWrapper([TestRenderer]+pf_ct.renderer_choices)
        self.setup_crud_page()


        self.update_pf_ct.variation = 'TestRenderer'
        self.update_pf_ct.save()


        
        response = self.client.post(self.page._cached_url,
                            data={'test22_second_col_0-domain':'a',
                                  'test22_second_col_0-name':'b',
                                  'test22_second_col_0_update':'submit'})
        
        self.assert_(response.status_code == 302)
        self.assert_(self.page._cached_url in response['Location'])

    def test_unsuccessful_update_with_success_action(self):
        class TestRenderer(UpdatePublicForm):
             success_action = True
        
        pf_ct = module_content_type(Page, PublicForm)
        self.orig_render = pf_ct.render
        pf_ct.render = RendererSelectionWrapper([TestRenderer]+pf_ct.renderer_choices)
        self.setup_crud_page()


        self.update_pf_ct.variation = 'TestRenderer'
        self.update_pf_ct.save()
        
        response = self.client.post(self.page._cached_url,
                            data={'test22_second_col_0-domain':'',
                                  'test22_second_col_0-name':'notupdated',
                                  'test22_second_col_0_update':'submit'})
        
        self.assert_(response.status_code == 200)
        self.assert_('errorlist' in response.content)
        self.assert_(unicode(Site.objects.get(id=1).name) \
                     is not unicode('notupdated'))

    def test_successful_delete_with_success_action(self):
        class TestRenderer(DeletePublicForm):
             success_action = True
        
        pf_ct = module_content_type(Page, PublicForm)
        self.orig_render = pf_ct.render
        pf_ct.render = RendererSelectionWrapper([TestRenderer]+pf_ct.renderer_choices)
        self.setup_crud_page()


        self.delete_pf_ct.variation = 'TestRenderer'
        self.delete_pf_ct.save()

        sites_n = Site.objects.all().count()
        response = self.client.post(self.page._cached_url,
                            data={'test22_third_col_0_delete':'submit'})

        self.assert_(response.status_code == 302)
        self.assert_(self.page._cached_url in response['Location'])
        self.assert_(Site.objects.filter(id=1).count() == 0)



    def test_successful_update(self):
        self.setup_crud_page()
        response = self.client.post(self.page._cached_url,
                            data={'test22_second_col_0-domain':'updated',
                                  'test22_second_col_0-name':'updated',
                                  'test22_second_col_0_update':'submit'})
        
        self.assert_('errorlist' not in response.content)                                
        self.assert_(Site.objects.get(id=1).domain == 'updated')
        self.assert_(Site.objects.get(id=1).name == 'updated')

    def test_successful_delete(self):
        self.setup_crud_page()
        response = self.client.post(self.page._cached_url,
                            data={'test22_third_col_0_delete':'submit'})
        self.assert_('errorlist' not in response.content)
        self.assert_(Site.objects.filter(id=1).count() == 0)

    def test_unsuccessful_create(self):
        self.setup_crud_page()
        sites_n = Site.objects.all().count()
        response = self.client.post(self.page._cached_url,
                            data={'test22_first_col_0-domain':'',
                                  'test22_first_col_0-name':'b',
                                  'test22_first_col_0_create':'submit'})

        self.assert_(response.content=="""<div class="page-content"><form method='POST'><tr><th><label for="id_test22_first_col_0-domain">Domain name:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input id="id_test22_first_col_0-domain" type="text" name="test22_first_col_0-domain" maxlength="100" /></td></tr><tr><th><label for="id_test22_first_col_0-name">Display name:</label></th><td><input id="id_test22_first_col_0-name" type="text" name="test22_first_col_0-name" value="b" maxlength="50" /></td></tr><input type="submit" name="test22_first_col_0_create"/></form></div><div class="page-content"><form method='POST'><tr><th><label for="id_test22_second_col_0-domain">Domain name:</label></th><td><input id="id_test22_second_col_0-domain" type="text" name="test22_second_col_0-domain" value="example.com" maxlength="100" /></td></tr><tr><th><label for="id_test22_second_col_0-name">Display name:</label></th><td><input id="id_test22_second_col_0-name" type="text" name="test22_second_col_0-name" value="example.com" maxlength="50" /></td></tr><input type="submit" name="test22_second_col_0_update"/></form></div><div class="page-content"><form method='POST'><input type="submit" name="test22_third_col_0_delete"/></form></div>""")
        self.assert_(Site.objects.all().count() == sites_n)

    def test_unsuccessful_update(self):
        self.setup_crud_page()
        response = self.client.post(self.page._cached_url,
                            data={'test22_second_col_0-domain':'',
                                  'test22_second_col_0-name':'notupdated',
                                  'test22_second_col_0_update':'submit'})
        self.assert_(response.content=="""<div class="page-content"><form method='POST'><tr><th><label for="id_test22_first_col_0-domain">Domain name:</label></th><td><input id="id_test22_first_col_0-domain" type="text" name="test22_first_col_0-domain" maxlength="100" /></td></tr><tr><th><label for="id_test22_first_col_0-name">Display name:</label></th><td><input id="id_test22_first_col_0-name" type="text" name="test22_first_col_0-name" maxlength="50" /></td></tr><input type="submit" name="test22_first_col_0_create"/></form></div><div class="page-content"><form method='POST'><tr><th><label for="id_test22_second_col_0-domain">Domain name:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input id="id_test22_second_col_0-domain" type="text" name="test22_second_col_0-domain" maxlength="100" /></td></tr><tr><th><label for="id_test22_second_col_0-name">Display name:</label></th><td><input id="id_test22_second_col_0-name" type="text" name="test22_second_col_0-name" value="notupdated" maxlength="50" /></td></tr><input type="submit" name="test22_second_col_0_update"/></form></div><div class="page-content"><form method='POST'><input type="submit" name="test22_third_col_0_delete"/></form></div>""")
        self.assert_(Site.objects.get(id=1).name != 'notupdated')


class MultiformCRUDTest(MultiformCRUDTestMixin, CRUDTest):
    page_template_text = """{%spaceless%}{% load feincms_tags %}
        <div class="page-content">{% feincms_render_region feincms_page "first_col" request %}</div>
        <div class="page-content">{% feincms_render_region feincms_page "second_col" request %}</div>
        <div class="page-content">{% feincms_render_region feincms_page "third_col" request %}</div>{%endspaceless%}"""

    def create_templates(self):
        for action in ('create', 'update', 'delete'):        
            self.setup_template('content/sites/site_%s.html'%action,
                                """<form method='POST'>{{form}}<input type="submit" name="{{form.submit_name}}"/></form>"""
                               )

class SingleFormWithFormsetsCRUDTest(MultiformCRUDTestMixin, CRUDTest):
    page_template_text = """{%spaceless%}{% load feincms_tags %}{% if feincms_page.contains_forms%}<form method='POST'>{%endif%}
        <div class="page-content">{% feincms_render_region feincms_page "first_col" request %}</div>
        <div class="page-content">{% feincms_render_region feincms_page "second_col" request %}</div>
        <div class="page-content">{% feincms_render_region feincms_page "third_col" request %}</div>
        {% if feincms_page.contains_forms%}</form>{%endif%}
        {%endspaceless%}"""

    def create_templates(self):
        for action in ('create', 'update', 'delete'):        
            self.setup_template('content/sites/site_%s.html'%action,
                                """<fieldset>{{form}}<input type="submit" name="{{form.submit_name}}"/></fieldset>"""
                                )

    def test_unsuccessful_create(self):
        self.setup_crud_page()
        sites_n = Site.objects.all().count()
        response = self.client.post(self.page._cached_url,
                            data={'test22_first_col_0-domain':'',
                                  'test22_first_col_0-name':'b',
                                  'test22_first_col_0_create':'submit'})

        self.assert_(response.content=="""<form method='POST'><div class="page-content"><fieldset><tr><th><label for="id_test22_first_col_0-domain">Domain name:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input id="id_test22_first_col_0-domain" type="text" name="test22_first_col_0-domain" maxlength="100" /></td></tr><tr><th><label for="id_test22_first_col_0-name">Display name:</label></th><td><input id="id_test22_first_col_0-name" type="text" name="test22_first_col_0-name" value="b" maxlength="50" /></td></tr><input type="submit" name="test22_first_col_0_create"/></fieldset></div><div class="page-content"><fieldset><tr><th><label for="id_test22_second_col_0-domain">Domain name:</label></th><td><input id="id_test22_second_col_0-domain" type="text" name="test22_second_col_0-domain" value="example.com" maxlength="100" /></td></tr><tr><th><label for="id_test22_second_col_0-name">Display name:</label></th><td><input id="id_test22_second_col_0-name" type="text" name="test22_second_col_0-name" value="example.com" maxlength="50" /></td></tr><input type="submit" name="test22_second_col_0_update"/></fieldset></div><div class="page-content"><fieldset><input type="submit" name="test22_third_col_0_delete"/></fieldset></div></form>""")
        self.assert_(Site.objects.all().count() == sites_n)

    def test_unsuccessful_update(self):
        self.setup_crud_page()
        response = self.client.post(self.page._cached_url,
                            data={'test22_second_col_0-domain':'',
                                  'test22_second_col_0-name':'notupdated',
                                  'test22_second_col_0_update':'submit'})
        self.assert_(response.content=="""<form method='POST'><div class="page-content"><fieldset><tr><th><label for="id_test22_first_col_0-domain">Domain name:</label></th><td><input id="id_test22_first_col_0-domain" type="text" name="test22_first_col_0-domain" maxlength="100" /></td></tr><tr><th><label for="id_test22_first_col_0-name">Display name:</label></th><td><input id="id_test22_first_col_0-name" type="text" name="test22_first_col_0-name" maxlength="50" /></td></tr><input type="submit" name="test22_first_col_0_create"/></fieldset></div><div class="page-content"><fieldset><tr><th><label for="id_test22_second_col_0-domain">Domain name:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input id="id_test22_second_col_0-domain" type="text" name="test22_second_col_0-domain" maxlength="100" /></td></tr><tr><th><label for="id_test22_second_col_0-name">Display name:</label></th><td><input id="id_test22_second_col_0-name" type="text" name="test22_second_col_0-name" value="notupdated" maxlength="50" /></td></tr><input type="submit" name="test22_second_col_0_update"/></fieldset></div><div class="page-content"><fieldset><input type="submit" name="test22_third_col_0_delete"/></fieldset></div></form>""")
#        self.assert_(Site.objects.get(id=1).name != 'notupdated')


class PublicFormCaptchaTests(FeincmsPageTestCase):
    def test_non_authenticated_captcha_enabled_once_create(self):
        site_content_type = ContentType.objects.\
                                 get_for_model(Site)
        
        create_pf_kwargs = {
                 'region':'first_col',
                 'enable_captcha_once':True,
                 'enable_captcha_always':False,
                 'enable_ajax':False,
                 'object_id':None,
                 'content_type':site_content_type,
                 'variation':'CreatePublicForm',
                 'parent':self.page,
                 'ordering':0}

        self.pf_ct = module_content_type(Page, PublicForm)
        self.create_pf_ct = self.pf_ct(**create_pf_kwargs)
        self.create_pf_ct.save()

        request = self.factory.get(self.page._cached_url)
        
        self.assert_(self.create_pf_ct.render.is_captcha_required(request))
        request.session[CAPTCHA_PASSED_SESSION_KEY] = True
        self.assert_(not self.create_pf_ct.render.is_captcha_required(request))

    def test_non_authenticated_captcha_enabled_once_update(self):
        site_content_type = ContentType.objects.\
                                 get_for_model(Site)
        
        update_pf_kwargs = {
                 'region':'first_col',
                 'enable_captcha_once':True,
                 'enable_captcha_always':False,
                 'enable_ajax':False,
                 'object_id':None,
                 'content_type':site_content_type,
                 'variation':'UpdatePublicForm',
                 'parent':self.page,
                 'ordering':0}

        self.pf_ct = module_content_type(Page, PublicForm)
        self.update_pf_ct = self.pf_ct(**update_pf_kwargs)
        self.update_pf_ct.save()

        request = self.factory.get(self.page._cached_url)
        
        self.assert_(self.update_pf_ct.render.is_captcha_required(request))
        request.session[CAPTCHA_PASSED_SESSION_KEY] = True
        self.assert_(not self.update_pf_ct.render.is_captcha_required(request))

    def test_non_authenticated_captcha_enabled_once_delete(self):
        site_content_type = ContentType.objects.\
                                 get_for_model(Site)
        
        delete_pf_kwargs = {
                 'region':'first_col',
                 'enable_captcha_once':True,
                 'enable_captcha_always':False,
                 'enable_ajax':False,
                 'object_id':None,
                 'content_type':site_content_type,
                 'variation':'DeletePublicForm',
                 'parent':self.page,
                 'ordering':0}

        self.pf_ct = module_content_type(Page, PublicForm)
        self.delete_pf_ct = self.pf_ct(**delete_pf_kwargs)
        self.delete_pf_ct.save()

        request = self.factory.get(self.page._cached_url)
        
        self.assert_(self.delete_pf_ct.render.is_captcha_required(request))
        request.session[CAPTCHA_PASSED_SESSION_KEY] = True
        self.assert_(not self.delete_pf_ct.render.is_captcha_required(request))

    def test_non_authenticated_captcha_enabled_always_create(self):
        site_content_type = ContentType.objects.\
                                 get_for_model(Site)
        
        create_pf_kwargs = {
                 'region':'first_col',
                 'enable_captcha_once':False,
                 'enable_captcha_always':True,
                 'enable_ajax':False,
                 'object_id':None,
                 'content_type':site_content_type,
                 'variation':'CreatePublicForm',
                 'parent':self.page,
                 'ordering':0}

        self.pf_ct = module_content_type(Page, PublicForm)
        self.create_pf_ct = self.pf_ct(**create_pf_kwargs)
        self.create_pf_ct.save()

        request = self.factory.get(self.page._cached_url)
        
        self.assert_(self.create_pf_ct.render.is_captcha_required(request))
        request.session[CAPTCHA_PASSED_SESSION_KEY] = True
        self.assert_(self.create_pf_ct.render.is_captcha_required(request))

    def test_non_authenticated_captcha_enabled_always_update(self):
        site_content_type = ContentType.objects.\
                                 get_for_model(Site)
        
        update_pf_kwargs = {
                 'region':'first_col',
                 'enable_captcha_once':False,
                 'enable_captcha_always':True,
                 'enable_ajax':False,
                 'object_id':None,
                 'content_type':site_content_type,
                 'variation':'UpdatePublicForm',
                 'parent':self.page,
                 'ordering':0}

        self.pf_ct = module_content_type(Page, PublicForm)
        self.update_pf_ct = self.pf_ct(**update_pf_kwargs)
        self.update_pf_ct.save()

        request = self.factory.get(self.page._cached_url)
        
        self.assert_(self.update_pf_ct.render.is_captcha_required(request))
        request.session[CAPTCHA_PASSED_SESSION_KEY] = True
        self.assert_(self.update_pf_ct.render.is_captcha_required(request))

    def test_non_authenticated_captcha_enabled_always_delete(self):
        site_content_type = ContentType.objects.\
                                 get_for_model(Site)
        
        delete_pf_kwargs = {
                 'region':'first_col',
                 'enable_captcha_once':False,
                 'enable_captcha_always':True,
                 'enable_ajax':False,
                 'object_id':None,
                 'content_type':site_content_type,
                 'variation':'DeletePublicForm',
                 'parent':self.page,
                 'ordering':0}

        self.pf_ct = module_content_type(Page, PublicForm)
        self.delete_pf_ct = self.pf_ct(**delete_pf_kwargs)
        self.delete_pf_ct.save()

        request = self.factory.get(self.page._cached_url)
        
        self.assert_(self.delete_pf_ct.render.is_captcha_required(request))
        request.session[CAPTCHA_PASSED_SESSION_KEY] = True
        self.assert_(self.delete_pf_ct.render.is_captcha_required(request))

    def test_authenticated_captcha_enabled_once_create(self):
        site_content_type = ContentType.objects.\
                                 get_for_model(Site)
        
        create_pf_kwargs = {
                 'region':'first_col',
                 'enable_captcha_once':True,
                 'enable_captcha_always':False,
                 'enable_ajax':False,
                 'object_id':None,
                 'content_type':site_content_type,
                 'variation':'CreatePublicForm',
                 'parent':self.page,
                 'ordering':0}

        self.pf_ct = module_content_type(Page, PublicForm)
        self.create_pf_ct = self.pf_ct(**create_pf_kwargs)
        self.create_pf_ct.save()

        request = self.factory.get(self.page._cached_url)
        login(request, authenticate(username='admin', password='admin'))
        
        self.assert_(not self.create_pf_ct.render.is_captcha_required(request))
        request.session[CAPTCHA_PASSED_SESSION_KEY] = True
        self.assert_(not self.create_pf_ct.render.is_captcha_required(request))

    def test_authenticated_captcha_enabled_once_update(self):
        site_content_type = ContentType.objects.\
                                 get_for_model(Site)
        
        update_pf_kwargs = {
                 'region':'first_col',
                 'enable_captcha_once':True,
                 'enable_captcha_always':False,
                 'enable_ajax':False,
                 'object_id':None,
                 'content_type':site_content_type,
                 'variation':'UpdatePublicForm',
                 'parent':self.page,
                 'ordering':0}

        self.pf_ct = module_content_type(Page, PublicForm)
        self.update_pf_ct = self.pf_ct(**update_pf_kwargs)
        self.update_pf_ct.save()

        request = self.factory.get(self.page._cached_url)
        login(request, authenticate(username='admin', password='admin'))
        
        self.assert_(not self.update_pf_ct.render.is_captcha_required(request))
        request.session[CAPTCHA_PASSED_SESSION_KEY] = True
        self.assert_(not self.update_pf_ct.render.is_captcha_required(request))

    def test_authenticated_captcha_enabled_once_delete(self):
        site_content_type = ContentType.objects.\
                                 get_for_model(Site)
        
        delete_pf_kwargs = {
                 'region':'first_col',
                 'enable_captcha_once':True,
                 'enable_captcha_always':False,
                 'enable_ajax':False,
                 'object_id':None,
                 'content_type':site_content_type,
                 'variation':'DeletePublicForm',
                 'parent':self.page,
                 'ordering':0}

        self.pf_ct = module_content_type(Page, PublicForm)
        self.delete_pf_ct = self.pf_ct(**delete_pf_kwargs)
        self.delete_pf_ct.save()

        request = self.factory.get(self.page._cached_url)
        login(request, authenticate(username='admin', password='admin'))
        
        self.assert_(not self.delete_pf_ct.render.is_captcha_required(request))
        request.session[CAPTCHA_PASSED_SESSION_KEY] = True
        self.assert_(not self.delete_pf_ct.render.is_captcha_required(request))

    def test_authenticated_captcha_enabled_always_create(self):
        site_content_type = ContentType.objects.\
                                 get_for_model(Site)
        
        create_pf_kwargs = {
                 'region':'first_col',
                 'enable_captcha_once':False,
                 'enable_captcha_always':True,
                 'enable_ajax':False,
                 'object_id':None,
                 'content_type':site_content_type,
                 'variation':'CreatePublicForm',
                 'parent':self.page,
                 'ordering':0}

        self.pf_ct = module_content_type(Page, PublicForm)
        self.create_pf_ct = self.pf_ct(**create_pf_kwargs)
        self.create_pf_ct.save()

        request = self.factory.get(self.page._cached_url)
        login(request, authenticate(username='admin', password='admin'))
        
        self.assert_(not self.create_pf_ct.render.is_captcha_required(request))
        request.session[CAPTCHA_PASSED_SESSION_KEY] = True
        self.assert_(not self.create_pf_ct.render.is_captcha_required(request))

    def test_authenticated_captcha_enabled_always_update(self):
        site_content_type = ContentType.objects.\
                                 get_for_model(Site)
        
        update_pf_kwargs = {
                 'region':'first_col',
                 'enable_captcha_once':False,
                 'enable_captcha_always':True,
                 'enable_ajax':False,
                 'object_id':None,
                 'content_type':site_content_type,
                 'variation':'UpdatePublicForm',
                 'parent':self.page,
                 'ordering':0}

        self.pf_ct = module_content_type(Page, PublicForm)
        self.update_pf_ct = self.pf_ct(**update_pf_kwargs)
        self.update_pf_ct.save()

        request = self.factory.get(self.page._cached_url)
        login(request, authenticate(username='admin', password='admin'))
        
        self.assert_(not self.update_pf_ct.render.is_captcha_required(request))
        request.session[CAPTCHA_PASSED_SESSION_KEY] = True
        self.assert_(not self.update_pf_ct.render.is_captcha_required(request))

    def test_authenticated_captcha_enabled_always_delete(self):
        site_content_type = ContentType.objects.\
                                 get_for_model(Site)
        
        delete_pf_kwargs = {
                 'region':'first_col',
                 'enable_captcha_once':False,
                 'enable_captcha_always':True,
                 'enable_ajax':False,
                 'object_id':None,
                 'content_type':site_content_type,
                 'variation':'DeletePublicForm',
                 'parent':self.page,
                 'ordering':0}

        self.pf_ct = module_content_type(Page, PublicForm)
        self.delete_pf_ct = self.pf_ct(**delete_pf_kwargs)
        self.delete_pf_ct.save()

        request = self.factory.get(self.page._cached_url)
        login(request, authenticate(username='admin', password='admin'))
        
        self.assert_(not self.delete_pf_ct.render.is_captcha_required(request))
        request.session[CAPTCHA_PASSED_SESSION_KEY] = True
        self.assert_(not self.delete_pf_ct.render.is_captcha_required(request))

    def test_captcha_field_appended_if_captcha_required_on_create(self):
        site_content_type = ContentType.objects.\
                                 get_for_model(Site)
        
        create_pf_kwargs = {
                 'region':'first_col',
                 'enable_captcha_once':False,
                 'enable_captcha_always':True,
                 'enable_ajax':False,
                 'object_id':None,
                 'content_type':site_content_type,
                 'variation':'CreatePublicForm',
                 'parent':self.page,
                 'ordering':0}

        orig_get_form = CreatePublicForm.get_form
        mutable_form_store = {}
        def get_form(self, *args, **kwargs):
            form = orig_get_form.__get__(self, CreatePublicForm)(*args, **kwargs)
            mutable_form_store['form'] = form
            return form

        CreatePublicForm.get_form = get_form.__get__(None, CreatePublicForm)
        try:
            pf_ct = module_content_type(Page, PublicForm)
            create_pf_ct = pf_ct(**create_pf_kwargs)
            create_pf_ct.save()
            
            create_pf_ct.render.get_form = get_form.__get__(create_pf_ct.render,
                                                            create_pf_ct.render.__class__)
            response = self.client.get(self.page._cached_url)
            self.assert_(settings.PUBLIC_FORMS_CAPTCHA_FIELD_NAME in mutable_form_store['form'].fields)
        finally:
            CreatePublicForm.get_form = orig_get_form

    def test_captcha_field_appended_if_captcha_required_on_update(self):
        site_content_type = ContentType.objects.\
                                 get_for_model(Site)
        
        update_pf_kwargs = {
                 'region':'first_col',
                 'enable_captcha_once':False,
                 'enable_captcha_always':True,
                 'enable_ajax':False,
                 'object_id':None,
                 'content_type':site_content_type,
                 'variation':'UpdatePublicForm',
                 'parent':self.page,
                 'ordering':0}

        orig_get_form = UpdatePublicForm.get_form
        mutable_form_store = {}
        def get_form(self, *args, **kwargs):
            form = orig_get_form.__get__(self, UpdatePublicForm)(*args, **kwargs)
            mutable_form_store['form'] = form
            return form

        UpdatePublicForm.get_form = get_form.__get__(None, UpdatePublicForm)
        try:
            pf_ct = module_content_type(Page, PublicForm)
            update_pf_ct = pf_ct(**update_pf_kwargs)
            update_pf_ct.save()
            
            update_pf_ct.render.get_form = get_form.__get__(update_pf_ct.render,
                                                            update_pf_ct.render.__class__)
            response = self.client.get(self.page._cached_url)
            self.assert_(settings.PUBLIC_FORMS_CAPTCHA_FIELD_NAME in mutable_form_store['form'].fields)
        finally:
            UpdatePublicForm.get_form = orig_get_form

    def test_captcha_field_appended_if_captcha_required_on_delete(self):
        site_content_type = ContentType.objects.\
                                 get_for_model(Site)
        
        delete_pf_kwargs = {
                 'region':'first_col',
                 'enable_captcha_once':False,
                 'enable_captcha_always':True,
                 'enable_ajax':False,
                 'object_id':None,
                 'content_type':site_content_type,
                 'variation':'DeletePublicForm',
                 'parent':self.page,
                 'ordering':0}

        orig_get_form = DeletePublicForm.get_form
        mutable_form_store = {}
        def get_form(self, *args, **kwargs):
            form = orig_get_form.__get__(self, DeletePublicForm)(*args, **kwargs)
            mutable_form_store['form'] = form
            return form

        DeletePublicForm.get_form = get_form.__get__(None, DeletePublicForm)
        try:
            pf_ct = module_content_type(Page, PublicForm)
            delete_pf_ct = pf_ct(**delete_pf_kwargs)
            delete_pf_ct.save()
            
            delete_pf_ct.render.get_form = get_form.__get__(delete_pf_ct.render,
                                                            delete_pf_ct.render.__class__)
            response = self.client.get(self.page._cached_url)
            self.assert_(settings.PUBLIC_FORMS_CAPTCHA_FIELD_NAME in mutable_form_store['form'].fields)
        finally:
            DeletePublicForm.get_form = orig_get_form


class RendererMediaTest(CRUDTest):
    page_template_text = """{%spaceless%}{% load feincms_tags %}!{{ feincms_page.content.media }}!
    <div class="page-content">{% feincms_render_region feincms_page "first_col" request %}</div>
    <div class="page-content">{% feincms_render_region feincms_page "second_col" request %}</div>
    <div class="page-content">{% feincms_render_region feincms_page "third_col" request %}</div>{%endspaceless%}"""

    def create_templates(self):
        for action in ('create', 'update', 'delete'):        
            self.setup_template('content/sites/site_%s.html'%action,
                                """<form method='POST'>{{form}}<input type="submit" name="{{form.submit_name}}"/></form>"""
                               )


    def setup_crud_page(self):
        self.site_content_type = ContentType.objects.\
                                 get_for_model(Site)
        
        self.create_pf_kwargs = {
                 'region':'first_col',
                 'enable_captcha_once':False,
                 'enable_captcha_always':True,
                 'enable_ajax':False,
                 'object_id':None,
                 'content_type':self.site_content_type,
                 'variation':'CreatePublicForm',
                 'parent':self.page,
                 'ordering':0}

        self.update_pf_kwargs = {
                 'region':'second_col',
                 'enable_captcha_once':False,
                 'enable_captcha_always':True,
                 'enable_ajax':False,
                 'object_id':1,
                 'content_type':self.site_content_type,
                 'variation':'UpdatePublicForm',
                 'parent':self.page,
                 'ordering':0}
                 
        self.delete_pf_kwargs = {
                 'region':'third_col',
                 'enable_captcha_once':False,
                 'enable_captcha_always':True,
                 'enable_ajax':False,
                 'object_id':1,
                 'content_type':self.site_content_type,
                 'variation':'DeletePublicForm',
                 'parent':self.page,
                 'ordering':0}
                                          
        self.pf_ct = module_content_type(Page, PublicForm)
        self.create_pf_ct = self.pf_ct(**self.create_pf_kwargs)
        self.create_pf_ct.save()

        self.update_pf_ct = self.pf_ct(**self.update_pf_kwargs)
        self.update_pf_ct.save()

        self.delete_pf_ct = self.pf_ct(**self.delete_pf_kwargs)
        self.delete_pf_ct.save()
        self.create_templates()
    def test_create_public_form_media(self):
        class TestFormClass(ModelForm):
            class Meta:
                model = Site
            class Media:
                js=('form/class/media.js',)
                css={'all': ('form/class/media.css',),}
            
            captcha = ReCaptchaFieldAjax()
        
        class TestRenderer(CreatePublicForm):
            media = Media(
                        css={'all': ('renderer/media.css',),},
                        js=('renderer/media.js',),
                        )
            form_class = TestFormClass
        
        pf_ct = module_content_type(Page, PublicForm)
        self.orig_render = pf_ct.render
        pf_ct.render = RendererSelectionWrapper([TestRenderer]+pf_ct.renderer_choices)
        self.setup_crud_page()

        
        self.create_pf_ct.variation = 'TestRenderer'
        self.create_pf_ct.save()


        response = self.client.get(self.page._cached_url)

        for mediapath in ("renderer/media.css",
                          "form/class/media.css",
                          "renderer/media.js",
                          "recaptcha_ajax.js",
                          "captcha.js",
                          "form/class/media.js"):
            self.assert_(mediapath in response.content)

    def test_update_public_form_media(self):
        class TestFormClass(ModelForm):
            class Meta:
                model = Site
            class Media:
                js=('form/class/media.js',)
                css={'all': ('form/class/media.css',),}
            
        
        class TestRenderer(UpdatePublicForm):
            media = Media(
                        css={'all': ('renderer/media.css',),},
                        js=('renderer/media.js',),
                        )
            form_class = TestFormClass
        
        pf_ct = module_content_type(Page, PublicForm)
        self.orig_render = pf_ct.render
        pf_ct.render = RendererSelectionWrapper([TestRenderer]+pf_ct.renderer_choices)
        self.setup_crud_page()

        
        self.update_pf_ct.variation = 'TestRenderer'
        self.update_pf_ct.save()

    def test_delete_public_form_media(self):
        class TestFormClass(ModelForm):
            class Meta:
                model = Site
            class Media:
                js=('form/class/media.js',)
                css={'all': ('form/class/media.css',),}
        
        class TestRenderer(DeletePublicForm):
            media = Media(
                        css={'all': ('renderer/media.css',),},
                        js=('renderer/media.js',),
                        )
            form_class = TestFormClass
        
        pf_ct = module_content_type(Page, PublicForm)
        self.orig_render = pf_ct.render
        pf_ct.render = RendererSelectionWrapper([TestRenderer]+pf_ct.renderer_choices)
        self.setup_crud_page()

        
        self.delete_pf_ct.variation = 'TestRenderer'
        self.delete_pf_ct.save()

        response = self.client.get(self.page._cached_url)

        for mediapath in ("renderer/media.css",
                          "form/class/media.css",
                          "renderer/media.js",
                          "recaptcha_ajax.js",
                          "captcha.js",
                          "form/class/media.js"):
            self.assert_(mediapath in response.content)
            
class PublicFormAjaxTests(object):
    pass