import os
__all__ = ('settings',)
APP_NAME = os.path.basename(os.path.dirname(__file__))
class LazySettings(object):
    settings_prefix = APP_NAME.upper()
    def __init__(self):
        self._settings_loaded = False
    def _load_settings(self):
        self._settings_loaded = True
        from . import default_settings
        from django.conf import settings as django_settings
        self.django_settings = django_settings
        for key in dir(default_settings):
            if not key.isupper():
                continue
            prefixed_key = '%s_%s'%(self.settings_prefix, key)
            setattr(self, 
                    prefixed_key,
                    getattr(django_settings, 
                            prefixed_key,
                            getattr(default_settings, key)))

    def __getattr__(self, attr):
        if not self._settings_loaded:
            self._load_settings()
        
        return attr in self.__dict__ and\
               self.__dict__[attr] or\
               getattr(self.django_settings, attr)

settings = LazySettings()

page_available = False
try:
    from feincms.module.page.models import Page
    page_available = True
except ImportError:
    pass



if page_available:
    if not getattr(Page.register_extension, 'warnings_patched', False):
        orig_register_extension = Page.register_extension.__get__(None, Page)
        import warnings
        def raise_warning_if_no_intersection(current, required, setting_name):
            unsatisfied = (req for req in required if not req in current)
            for req in unsatisfied:
                warnings.warn('settings.%s does not contain `%s` entry, required for `%s` to work correctly'%(setting_name, req, APP_NAME))

        def register_extension(cls, register_fn):
            '''
                warns about unconfigured but required 
                    * middlewares
                    * context processors
                    * applications
                    #* urlconfs
                omits register_fn for excluded content types
            '''
            getattr(settings, 'ANYTHING', None)
            for setting_name, requires_list in (('MIDDLEWARE_CLASSES', '%s_REQUIRED_MIDDLEWARES'%APP_NAME),
                                                ('TEMPLATE_CONTEXT_PROCESSORS', '%s_REQUIRED_CONTEXT_PROCESSORS'%APP_NAME),
                                                ('INSTALLED_APPS', '%s_REQUIRED_APPLICATIONS'%APP_NAME)):
                raise_warning_if_no_intersection(getattr(settings, setting_name), 
                                                 getattr(settings, requires_list),
                                                 setting_name)
            orig_register_extension(register_fn)
        register_extension.warnings_patched = True
        Page.register_extension = classmethod(register_extension)

    Page.register_extensions('{project_namespace}.{egg_name}.models')
