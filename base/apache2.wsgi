import os
import sys

sys.path.append('/PATH/TO/UNALOG2PARENT/unalog2')

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()