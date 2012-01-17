from django.conf import settings

EXCLUDE_CONTENT_TYPES = []

REQUIRED_MIDDLEWARES = ['django.contrib.sessions.middleware.SessionMiddleware',]

REQUIRED_CONTEXT_PROCESSORS = []

REQUIRED_APPLICATIONS = ['feincms',
                         'feincms.page.extensions.variative_renderer',]

CAPTCHA_FIELD_NAME = 'captcha'

CONTENT_TYPES = (
                 'feincms.page.extensions.public_forms.models.PublicForm',
                 )

DEFAULT_ENABLE_CAPTCHA_ONCE = True
DEFAULT_ENABLE_CAPTCHA_ALWAYS = False
DEFAULT_ENABLE_AJAX = False

AJAX_INIT_TEMPLATE = 'forms/ajax_init.html'