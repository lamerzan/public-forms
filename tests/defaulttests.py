from utility import VirtualProjectTestCase, chdir
import os
import time
class TestVirtualProject(VirtualProjectTestCase):
    test_settings = """
DATABASES = {{
'default': {{
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': '%s.db',
    'USER': '',
    'PASSWORD': '',
    'HOST': '',
    'PORT': '',
    }},
}}
DATABASE_ROUTERS=[]
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.webdesign',
    'django.contrib.staticfiles',
    'filebrowser',
    'mptt',
    'feincms.module.page',
    'feincms',
    '{package_namespace}.{egg_name}',
    'django.contrib.admin',
)    
MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.co33ntrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)
    """
    def test_package_importable(self):
        out = self.command('''python -c "from {package_namespace} import {egg_name}; print {egg_name}; print {egg_name}; print 333333;"''', output=True)
        out = '%s'%out
        self.assert_('{package_namespace}' in out)
        self.assert_('{egg_name}' in out)
        self.assert_('module' in out)
        self.assert_('333333' in out)

    def test_default_settings_importable(self):
        out = self.command('''python -c "from {package_namespace}.{egg_name} import settings; print settings; print 333333;"''', output=True)
        out = '%s'%out
        self.assert_('feincms.page.extensions' in out)
        self.assert_('{egg_name}' in out)
        self.assert_('LazySettings object' in out)
        self.assert_('333333' in out)


    def setUp(self):
        self.package_settings_path = os.path.join(self.testdir, self.project_package_name, 'settings.py')
        with open(self.package_settings_path) as package_settings:
            self.original_settings = package_settings.read()
        with open(self.package_settings_path, 'a') as package_settings:
            package_settings.write(self.test_settings)
        
    def tearDown(self):
        with open(self.package_settings_path, 'w') as package_settings:
            package_settings.write(self.original_settings)


    def test_run_package_tests(self):
        with chdir(os.path.join(self.testdir, self.project_package_name)):
            self.command('python manage.py test {egg_name}')

    
    def test_register_called(self):
        REGISTER_FN = """
def register(cls, admin_cls):
    with open('%s', 'w') as marker:
        marker.write("marker")
"""
        MARKER_PATH = os.path.join(self.testdir, 'marker')
        from pkg_resources import resource_filename
        models_path = resource_filename('{package_namespace}.{egg_name}', 'models.py')

        with open(models_path) as models:
            orig_models = models.read()
        
        try:
            with open(models_path, 'a') as models:
                models.write(REGISTER_FN%MARKER_PATH)
        
            with chdir(os.path.join(self.testdir, self.project_package_name)):
                self.command('python manage.py syncdb --noinput')

            self.assert_(os.path.exists(MARKER_PATH))
            os.remove(MARKER_PATH)
        finally:
            with open(models_path, 'w') as models:
                models.write(orig_models)


    def test_register_warns_about_required_middlewares(self):
        REQUIRED_MIDDLEWARES_SETTING = """\nREQUIRED_MIDDLEWARES = ['django.middleware.common.CommonMiddleware',]"""
        PROJECT_MIDDLEWARE_SETTING_WITHOUT_REQUIRED = """\nMIDDLEWARE_CLASSES = []"""
        PROJECT_MIDDLEWARE_SETTING_WITH_REQUIRED = """\nMIDDLEWARE_CLASSES = ['django.middleware.common.CommonMiddleware',]"""

        from pkg_resources import resource_filename
        default_settings_path = resource_filename('{package_namespace}.{egg_name}',
                                                  'default_settings.py')
        project_settings_path = os.path.join(self.testdir, self.project_package_name, 'settings.py')
        
        with open(default_settings_path) as default_settings:
            orig_default_settings = default_settings.read()
        
        with open(project_settings_path) as project_settings:
            orig_project_settings = project_settings.read()

        try:
            with open(default_settings_path, 'a') as default_settings:
                default_settings.write(REQUIRED_MIDDLEWARES_SETTING)

            with open(project_settings_path, 'a') as project_settings:
                project_settings.write(PROJECT_MIDDLEWARE_SETTING_WITHOUT_REQUIRED)
        
            with chdir(os.path.join(self.testdir, self.project_package_name)):

                out = self.command('python manage.py syncdb --noinput', 
                                         output=True)
                self.assert_('UserWarning:' in out)
                self.assert_('settings.MIDDLEWARE_CLASSES' in out)
                self.assert_('django.middleware.common.CommonMiddleware' in out)

        finally:
            with open(default_settings_path, 'w') as default_settings:
                default_settings.write(orig_default_settings)    
            time.sleep(0.1)#allow popen to close everything

    def test_register_warns_about_required_apps(self):
        REQUIRED_APPS_SETTING = """\nREQUIRED_APPLICATIONS = ['feincms',]"""
        PROJECT_APP_SETTING_WITHOUT_REQUIRED = """\nINSTALLED_APPS = ['{package_namespace}.{egg_name}',]"""


        from pkg_resources import resource_filename
        default_settings_path = resource_filename('{package_namespace}.{egg_name}',
                                                  'default_settings.py')
        project_settings_path = os.path.join(self.testdir, self.project_package_name, 'settings.py')
        
        with open(default_settings_path) as default_settings:
            orig_default_settings = default_settings.read()
        
        with open(project_settings_path) as project_settings:
            orig_project_settings = project_settings.read()

        try:
            with open(default_settings_path, 'a') as default_settings:
                default_settings.write(REQUIRED_APPS_SETTING)

            with open(project_settings_path, 'a') as project_settings:
                project_settings.write(PROJECT_APP_SETTING_WITHOUT_REQUIRED)
        
            with chdir(os.path.join(self.testdir, self.project_package_name)):

                out = self.command('python manage.py syncdb --noinput', 
                                         output=True)
                self.assert_('UserWarning:' in out)
                self.assert_('settings.INSTALLED_APPS' in out)
                self.assert_('feincms' in out)  

        finally:
            with open(default_settings_path, 'w') as default_settings:
                default_settings.write(orig_default_settings)    
            time.sleep(0.1)#allow popen to close everything

    def test_register_warns_about_required_context_processors(self):
        REQUIRED_CONTEXT_PROCESSOR_SETTING = """\nREQUIRED_CONTEXT_PROCESSORS = ['django.contrib.auth.context_processors.auth',]"""
        PROJECT_CONTEXT_PROCESSOR_SETTING_WITHOUT_REQUIRED = """\nTEMPLATE_CONTEXT_PROCESSORS = []"""

        from pkg_resources import resource_filename
        default_settings_path = resource_filename('{package_namespace}.{egg_name}',
                                                  'default_settings.py')
        project_settings_path = os.path.join(self.testdir, self.project_package_name, 'settings.py')
        
        with open(default_settings_path) as default_settings:
            orig_default_settings = default_settings.read()
        
        with open(project_settings_path) as project_settings:
            orig_project_settings = project_settings.read()

        try:
            with open(default_settings_path, 'a') as default_settings:
                default_settings.write(REQUIRED_CONTEXT_PROCESSOR_SETTING)

            with open(project_settings_path, 'a') as project_settings:
                project_settings.write(PROJECT_CONTEXT_PROCESSOR_SETTING_WITHOUT_REQUIRED)
        
            with chdir(os.path.join(self.testdir, self.project_package_name)):

                out = self.command('python manage.py syncdb --noinput', 
                                         output=True)

                self.assert_('UserWarning:' in out)
                self.assert_('settings.TEMPLATE_CONTEXT_PROCESSORS' in out)
                self.assert_('django.contrib.auth.context_processors.auth' in out)  

        finally:
            with open(default_settings_path, 'w') as default_settings:
                default_settings.write(orig_default_settings)    
            time.sleep(0.1)#allow popen to close everything