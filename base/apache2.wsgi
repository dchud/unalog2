import os
import sys

sys.path.append('/PATH/TO/UNALOG2PARENT')

os.environ['DJANGO_SETTINGS_MODULE'] = 'unalog2.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()