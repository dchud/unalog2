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
    # Site-wide
    url(r'^$', 'index', {'format': 'html'}, name='base-home'),
    url(r'^feed/$', 'index', {'format': 'atom'}),
    url(r'^tag/(?P<tag_name>[a-zA-Z0-9:._]+)/$', 'tag', name='base-tag'),
    url(r'^tag/(?P<tag_name>[a-zA-Z0-9:._]+)/feed/$', 'tag', 
        {'format': 'atom'}),
    
    # Users
    url(r'^user/(?P<user_name>[a-zA-Z0-9._]+)/$', 'user', {'format': 'html'},
        name='base-user'),
    url(r'^user/(?P<user_name>[a-zA-Z0-9._]+)/feed/$', 'user', {'format': 'atom'}),
    url(r'^user/(?P<user_name>[a-zA-Z0-9._]+)/tags/$', 'user_tags', 
        name='base-user-tags'),
    url(r'^user/(?P<user_name>[a-zA-Z0-9._]+)/tag/(?P<tag_name>[a-zA-Z0-9:._]+)/$', 
        'user_tag', name='base-user-tag'),
    url(r'^user/(?P<user_name>[a-zA-Z0-9._]+)/tag/(?P<tag_name>[a-zA-Z0-9:._]+)/feed/$', 
        'user_tag', {'format': 'atom'}),
    # Legacy url pattern - redirect.
    url(r'^person/(?P<user_name>.*)/$', 'person', name='base-person'),

    # Groups... looks very familiar...
    url(r'^group/(?P<group_name>[a-zA-Z0-9._]+)/$', 'group', name='base-group'),
    url(r'^group/(?P<group_name>[a-zA-Z0-9._]+)/feed/$', 'group', 
        {'format': 'atom'}),
    url(r'^group/(?P<group_name>[a-zA-Z0-9._]+)/tags/$', 'group_tags', 
        name='base-group-tags'),
    url(r'^group/(?P<group_name>[a-zA-Z0-9._]+)/tag/(?P<tag_name>[a-zA-Z0-9:._]+)/$', 
        'group_tag', name='base-group-tag'),
    url(r'^group/(?P<group_name>[a-zA-Z0-9._]+)/tag/(?P<tag_name>[a-zA-Z0-9:._]+)/feed/$', 
        'group_tag', {'format': 'atom'}),

    # URLs
    url(r'^url/(?P<md5sum>[a-f0-9]{32})/$', 'url_all'),
    url(r'^url/(?P<md5sum>[a-f0-9]{32})/feed/$', 'url_all', {'format': 'atom'}),
    
    )
