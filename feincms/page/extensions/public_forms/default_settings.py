from django.conf import settings

EXCLUDE_CONTENT_TYPES = []

REQUIRED_MIDDLEWARES = []

REQUIRED_CONTEXT_PROCESSORS = []

REQUIRED_APPLICATIONS = ['feincms',
                         'feincms.page.extensions.variative_renderer',]

DEFAULT_ENABLE_CAPTCHA = True
DEFAULT_ENABLE_AJAX = False