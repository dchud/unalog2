from django.conf.urls.defaults import *

from unalog2.settings import DEBUG, UNALOG_ROOT

urlpatterns = patterns('',
    (r'^$', 'unalog2.base.views.index'),

    # NOTE: don't enable this for real.
    (r'^s/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': "%s/base/media" % UNALOG_ROOT}),

    # Uncomment this for admin:
    (r'^admin/', include('django.contrib.admin.urls')),
)
