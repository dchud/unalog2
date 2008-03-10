from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # Example:
    # (r'^unalog2/', include('unalog2.foo.urls')),

    # Uncomment this for admin:
    (r'^admin/', include('django.contrib.admin.urls')),
)
