from utility import VirtualProjectTestCase, chdir
import os

class TestVirtualProject(VirtualProjectTestCase):
    settings = """
DATABASES = {{
'default': {{
    'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
    'NAME': '%s.db',                      # Or path to database file if using sqlite3.
    'USER': '',                      # Not used with sqlite3.
    'PASSWORD': '',                  # Not used with sqlite3.
    'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
    'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
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
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)
    """

    def test_package_importable(self):
        out, err = self.command('''python -c "from {package_namespace} import {egg_name}; print gridsystem; print 333333;"''', output=True)
        out = '%s'%out
        self.assert_('{package_namespace}' in out)
        self.assert_('{egg_name}' in out)
        self.assert_('module' in out)
        self.assert_('333333' in out)

    def test_default_settings_importable(self):
        out, err = self.command('''python -c "from {package_namespace}.{egg_name} import settings; print settings; print 333333;"''', output=True)
        out = '%s'%out
        self.assert_('{package_namespace}' in out)
        self.assert_('{egg_name}' in out)
        self.assert_('LazySettings object' in out)
        self.assert_('333333' in out)

    def test_run_package_tests(self):
        with chdir(os.path.join(self.testdir, self.project_package_name)):
            with open('settings.py', 'a') as settings:
                settings.write(self.settings%(self.project_package_name))
            self.command('python manage.py test {egg_name}')