from django.conf.urls.defaults import *
from django.contrib import admin

from unalog2.settings import UNALOG_ROOT

admin.autodiscover()


urlpatterns = patterns('',
    # NOTE: don't enable this for real.
    (r'^s/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': "%s/base/media" % UNALOG_ROOT}),

    url(r'^admin/(.*)', admin.site.root),

    url(r'^login/$', 'django.contrib.auth.views.login', 
        {'template_name': 'login.html'}, name='login'),

    )

urlpatterns += patterns('unalog2.base.views',
    # Site-wide
    url(r'^$', 'index', name='index'),
    url(r'^feed/$', 'feed_atom', name='feed_atom'),
    url(r'^logout/$', 'logout_view', name='logout'),
    url(r'^register/$', 'register_view', name='register'),
    url(r'^my/stack/link', 'old_stack_link', name='old_stack_link'),
    url(r'^indexing.js$', 'indexing_js', name='indexing_js'),
    url(r'^bookmarklet/$', 'bookmarklet', name='bookmarklet'),
    url(r'^about/$', 'about', name='about'),
    url(r'^contact/$', 'contact', name='contact'),
    
    # Entries
    url(r'^entry/(?P<entry_id>[0-9]+)$', 'entry', name='entry'),
    url(r'^entry/new', 'entry_new', name='entry_new'),
    url(r'^entry/(?P<entry_id>[0-9]+)/edit/$', 'entry_edit', 
        name='entry_edit'),
    url(r'^entry/(?P<entry_id>[0-9]+)/delete/$', 'entry_delete', 
        name='entry_delete'),
        
    
    url(r'^tags/$', 'tags', name='tags'),
    url(r'^tag/(?P<tag_name>[a-zA-Z0-9:._-]+)/$', 'tag', name='tag'),
    url(r'^tag/(?P<tag_name>[a-zA-Z0-9:._-]+)/feed/$', 'tag_atom', 
        name='tag_atom'),
    
    # Users
    url(r'^user/(?P<user_name>[a-zA-Z0-9._]+)/$', 'user', name='user'),
    url(r'^user/(?P<user_name>[a-zA-Z0-9._]+)/feed/$', 'user_atom', 
        name='user_atom'),
    url(r'^user/(?P<user_name>[a-zA-Z0-9._]+)/tags/$', 'user_tags', 
        name='user_tags'),
    url(r'^user/(?P<user_name>[a-zA-Z0-9._]+)/tag/(?P<tag_name>[a-zA-Z0-9:._-]+)/$', 
        'user_tag', name='user_tag'),
    url(r'^user/(?P<user_name>[a-zA-Z0-9._]+)/tag/(?P<tag_name>[a-zA-Z0-9:._-]+)/feed/$', 
        'user_tag_atom', name='user_tag_atom'),

    # Legacy url pattern - redirect.  No name assigned to discourage use.
    url(r'^person/(?P<user_name>.*)/$', 'person'),

    # Groups... looks very familiar...
    #url(r'^group/(?P<group_name>[a-zA-Z0-9._]+)/$', 'group', name='group'),
    #url(r'^group/(?P<group_name>[a-zA-Z0-9._]+)/feed/$', 'group_atom'),
    #url(r'^group/(?P<group_name>[a-zA-Z0-9._]+)/tags/$', 'group_tags', 
    #    name='group_tags'),
    #url(r'^group/(?P<group_name>[a-zA-Z0-9._]+)/tag/(?P<tag_name>[a-zA-Z0-9:._-]+)/$', 
    #    'group_tag', name='group_tag'),
    #url(r'^group/(?P<group_name>[a-zA-Z0-9._]+)/tag/(?P<tag_name>[a-zA-Z0-9:._-]+)/feed/$', 
    #    'group_tag_atom', name='group_tag_atom'),

    # URLs
    url(r'^url/(?P<md5sum>[a-f0-9]{32})/$', 'url', name='url'),
    url(r'^url/(?P<md5sum>[a-f0-9]{32})/feed/$', 'url_atom', 
        name='url_atom'),
    
    # Search
    url(r'^search/', 'search', name='search'),
    
    )
