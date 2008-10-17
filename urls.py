from django.conf.urls.defaults import *
from django.contrib import admin

from unalog2.settings import DEBUG, UNALOG_ROOT

admin.autodiscover()


urlpatterns = patterns('',
    # NOTE: don't enable this for real.
    (r'^s/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': "%s/base/media" % UNALOG_ROOT}),

    (r'^admin/(.*)', admin.site.root),

    url(r'^login/$', 'django.contrib.auth.views.login', 
        {'template_name': 'login.html'}),

    )

urlpatterns += patterns('unalog2.base.views',
    # Site-wide
    url(r'^$', 'index', {'format': 'html'}, name='base-home'),

    # TEST
    url(r'^my/stack/link', 'old_stack_link', name='old-stack-link'),
    url(r'^entry/url/new', 'new_url_entry', name='new-url-entry'),
    url(r'^indexing.js$', 'indexing_js', name='indexing-js'),
    
    
    url(r'^logout/$', 'logout_view', name='logout'),
    url(r'^register/$', 'register_view', name='register'),
    
    url(r'^feed/$', 'index', {'format': 'atom'}),

    url(r'^tags/$', 'tags_all', name='tags-all'),
    url(r'^tag/(?P<tag_name>[a-zA-Z0-9:._-]+)/$', 'tag', name='base-tag'),
    url(r'^tag/(?P<tag_name>[a-zA-Z0-9:._-]+)/feed/$', 'tag', 
        {'format': 'atom'}),
    
    # Users
    url(r'^user/(?P<user_name>[a-zA-Z0-9._]+)/$', 'user', {'format': 'html'},
        name='base-user'),
    url(r'^user/(?P<user_name>[a-zA-Z0-9._]+)/feed/$', 'user', {'format': 'atom'}),
    url(r'^user/(?P<user_name>[a-zA-Z0-9._]+)/tags/$', 'user_tags', 
        name='base-user-tags'),
    url(r'^user/(?P<user_name>[a-zA-Z0-9._]+)/tag/(?P<tag_name>[a-zA-Z0-9:._-]+)/$', 
        'user_tag', name='base-user-tag'),
    url(r'^user/(?P<user_name>[a-zA-Z0-9._]+)/tag/(?P<tag_name>[a-zA-Z0-9:._-]+)/feed/$', 
        'user_tag', {'format': 'atom'}),
    # Legacy url pattern - redirect.
    url(r'^person/(?P<user_name>.*)/$', 'person', name='base-person'),

    # Groups... looks very familiar...
    url(r'^group/(?P<group_name>[a-zA-Z0-9._]+)/$', 'group', name='base-group'),
    url(r'^group/(?P<group_name>[a-zA-Z0-9._]+)/feed/$', 'group', 
        {'format': 'atom'}),
    url(r'^group/(?P<group_name>[a-zA-Z0-9._]+)/tags/$', 'group_tag', 
        name='base-group-tags'),
    url(r'^group/(?P<group_name>[a-zA-Z0-9._]+)/tag/(?P<tag_name>[a-zA-Z0-9:._-]+)/$', 
        'group_tag', name='base-group-tag'),
    url(r'^group/(?P<group_name>[a-zA-Z0-9._]+)/tag/(?P<tag_name>[a-zA-Z0-9:._-]+)/feed/$', 
        'group_tag', {'format': 'atom'}),

    # URLs
    url(r'^url/(?P<md5sum>[a-f0-9]{32})/$', 'url_all'),
    url(r'^url/(?P<md5sum>[a-f0-9]{32})/feed/$', 'url_all', {'format': 'atom'}),
    
    )
