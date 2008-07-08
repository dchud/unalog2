from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^$', 'unalog2.base.views.index'),

    # Uncomment this for admin:
    (r'^admin/', include('django.contrib.admin.urls')),
)
