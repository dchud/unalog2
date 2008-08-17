from django.conf.urls.defaults import *

from unalog2.settings import DEBUG, UNALOG_ROOT

urlpatterns = patterns('',
    # NOTE: don't enable this for real.
    (r'^s/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': "%s/base/media" % UNALOG_ROOT}),

    # Uncomment this for admin:
    (r'^admin/', include('django.contrib.admin.urls')),
    )

urlpatterns += patterns('unalog2.base.views',
    url(r'^$', 'index', name='base-home'),
    url(r'^user/(?P<user_name>[a-zA-Z0-9_]+)/$', 'user', name='base-user'),
    url(r'^user/(?P<user_name>[a-zA-Z0-9_]+)/tags/$', 'user_tags', name='base-user-tags'),
    url(r'^user/(?P<user_name>[a-zA-Z0-9_]+)/tag/(?P<tag_name>.*)/$', 'user_tag', 
        name='base-user-tag'),
    # Legacy url pattern - redirect.
    url(r'^person/(?P<user_name>.*)/$', 'person', name='base-person'),
    url(r'^url/(?P<md5sum>[a-f0-9]{32})/$', 'url_all'),
    
    )
