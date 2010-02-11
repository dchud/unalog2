from django.conf.urls.defaults import *
from django.contrib import admin

from settings import UNALOG_ROOT

admin.autodiscover()


urlpatterns = patterns('',
    # NOTE: don't enable this for real.
    (r'^s/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': "%s/base/media" % UNALOG_ROOT}),

    url(r'^admin/(.*)', admin.site.root),

    url(r'^login/$', 'django.contrib.auth.views.login', 
        {'template_name': 'login.html'}, name='login'),

    )

urlpatterns += patterns('base.views',
    # Site-wide
    url(r'^$', 'index', name='index'),
    url(r'^feed/$', 'feed', name='feed'),
    url(r'^logout/$', 'logout_view', name='logout'),
    url(r'^register/$', 'register_view', name='register'),
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
    
    # Tags (site-wide)
    url(r'^tags/$', 'tags', name='tags'),
    url(r'^tag/(?P<tag_name>[+\w:._-]+)/$', 'tag', name='tag'),
    url(r'^tag/(?P<tag_name>[+\w:._-]+)/feed/$', 'tag_feed', 
        name='tag_feed'),
    
    # Users
    url(r'^user/(?P<user_name>[a-zA-Z0-9._]+)/$', 'user', name='user'),
    url(r'^user/(?P<user_name>[a-zA-Z0-9._]+)/feed/$', 'user_feed', 
        name='user_feed'),
    url(r'^user/(?P<user_name>[a-zA-Z0-9._]+)/tags/$', 'user_tags', 
        name='user_tags'),
    url(r'^user/(?P<user_name>[a-zA-Z0-9._]+)/tag/(?P<tag_name>[+\w:._-]+)/$', 
        'user_tag', name='user_tag'),
    url(r'^user/(?P<user_name>[a-zA-Z0-9._]+)/tag/(?P<tag_name>[+\w:._-]+)/feed/$', 
        'user_tag_feed', name='user_tag_feed'),

    # Filters
    url(r'^filter/$', 'filter_index', name='filter_index'),
    url(r'^filter/new/$', 'filter_new', name='filter_new'),

    # Legacy url pattern - redirect.  No name assigned to discourage use.
    url(r'^person/(?P<user_name>.*)/$', 'person'),

    # Groups... 
    url(r'^group/(?P<group_name>[a-zA-Z0-9._]+)/$', 'group', name='group'),
    url(r'^group/(?P<group_name>[a-zA-Z0-9._]+)/feed/$', 'group_feed', 
        name='group_feed'),
    # Punt on these for now.
    #url(r'^group/(?P<group_name>[a-zA-Z0-9._]+)/tags/$', 'group_tags', 
    #    name='group_tags'),
    #url(r'^group/(?P<group_name>[a-zA-Z0-9._]+)/tag/(?P<tag_name>[a-zA-Z0-9:._-]+)/$', 
    #    'group_tag', name='group_tag'),
    #url(r'^group/(?P<group_name>[a-zA-Z0-9._]+)/tag/(?P<tag_name>[a-zA-Z0-9:._-]+)/feed/$', 
    #    'group_tag_feed', name='group_tag_feed'),

    # URLs
    url(r'^url/(?P<md5sum>[a-f0-9]{32})/$', 'url', name='url'),
    url(r'^url/(?P<md5sum>[a-f0-9]{32})/feed/$', 'url_feed', name='url_feed'),
    
    # Search
    url(r'^search/$', 'search', name='search'),
    url(r'^search/feed/$', 'search_feed', name='search_feed'),
    
    )
