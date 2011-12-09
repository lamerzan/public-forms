import os
__all__ = ('settings',)
APP_NAME = os.path.dirname(__file__)
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
            # del self.__class__.__getattr__
        return attr in self.__dict__ and\
               self.__dict__[attr] or\
               getattr(self.django_settings, attr)

settings = LazySettings()