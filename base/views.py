import math
import re

from django.conf import settings
from django.contrib.auth import authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import login
from django.core.paginator import Paginator
from django import forms
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.http import HttpResponsePermanentRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, loader
from django.utils import feedgenerator

from solr import SolrConnection

from unalog2.base import models as m
from unalog2.settings import SOLR_URL

class UrlEntryForm(forms.Form):
    url = forms.URLField(required=True, label='URL')
    title = forms.CharField(required=True)
    tags = forms.CharField(required=False, help_text='Separate with spaces')
    is_private = forms.BooleanField(required=False)
    comment = forms.CharField(required=False, widget=forms.Textarea)
    content = forms.CharField(required=False, widget=forms.Textarea)


def standard_entries():
    """
    Start a base queryset of entries common to many pages.
    """
    qs = m.Entry.objects.exclude(user__is_active=False)
    # Note:  on the following, qs.exclude...=True blows up.
    qs = qs.filter(user__userprofile__is_private=False)
    qs = qs.exclude(is_private=True)
    qs = qs.order_by('-date_created')
    return qs


def get_page(request, paginator):
    try:
        page_num = int(request.GET.get('p', '1'))
        if page_num not in paginator.page_range:
            raise ValueError, 'Invalid page number'
    except ValueError:
        page_num = 1
    return paginator.page(page_num)
    

def pagify(request, qs):
    """
    Convenience helper to paginate out a query set.
    """
    paginator = Paginator(qs, 50)
    page = get_page(request, paginator)
    return paginator, page


def old_stack_link(request):
    """
    Redirect from old bookmarklet path.
    """
    return HttpResponseRedirect('/entry/url/new')
    

BAD_CHARS = """ ~`@#$%^&*()?\/,<>;\"'"""
RE_BAD_CHARS = re.compile(r'[%s]' % BAD_CHARS)

@login_required
def new_url_entry(request):
    """
    Save a new URL entry.
    """
    context = RequestContext(request)
    d = {}
    if request.method == 'POST':
        form = UrlEntryForm(request.POST)
        if form.is_valid():
            url_str = form.cleaned_data['url']
            title = form.cleaned_data['title']
            is_private = form.cleaned_data['is_private']
            tags_orig = form.cleaned_data['tags']
            comment = form.cleaned_data['comment']
            content = form.cleaned_data['content']
            
            new_entry = m.Entry(user=request.user, title=title, 
                is_private=is_private,
                comment=comment, content=content)

            url, was_created = m.Url.objects.get_or_create(value=url_str)
            new_entry.url = url
            
            # Save that sucker before adding many-to-manys
            new_entry.save()
            
            tag_strs = tags_orig.split(' ')
            # Remove repeats
            for tag in tag_strs:
                while tag_strs.count(tag) > 1:
                    tag_strs.remove(tag)
            # Remove empty tags like ''
            tag_strs = [tag for tag in tag_strs if not tag == '']
            # Remove bad tags, for bad chars or too lengthy
            for tag_str in tag_strs:
                if RE_BAD_CHARS.search(tag_str):
                    tag_strs.remove(tag_str)
                elif len(tag_str) > 30:
                    tag_strs.remove(tag_str)
            # Build up and add real tag objects
            for tag_str in tag_strs:
                tag, was_created = m.Tag.objects.get_or_create(name=tag_str)
                new_entry.tags.add(tag)

            request.user.message_set.create(message='Saved your entry.')
            return HttpResponseRedirect('/entry/%s/edit' % new_entry.id)
    else:
        form = UrlEntryForm()
    return render_to_response('new_entry.html', {'form': form}, context)


@login_required
def delete_url_entry(request, entry_id):
    """
    Let a user choose to delete an entry.
    """
    context = RequestContext(request)
    entry = get_object_or_404(m.Entry, id=entry_id)
    if entry.user != request.user:
        request.user.message_set.create(
            message="You can't go and delete other people's stuff like that, dude.")
        return HttpRequestRedirect('/')
    if request.method == 'POST':
        was_confirmed = request.POST['submit']
        if was_confirmed == 'yes':
            entry.delete()
            message = 'Deleted entry %s' % entry_id
            request.user.message_set.create(message=message)
            return HttpResponseRedirect('/')
    return render_to_response('delete_entry.html', 
        {'entry': entry}, context)


def url_entry(request, entry_id):
    """
    View an existing entry.
    """
    context = RequestContext(request)
    entry = get_object_or_404(m.Entry, id=entry_id)
    return render_to_response('url_entry.html', {'entry': entry}, context)


@login_required
def edit_url_entry(request, entry_id):
    """
    Update an existing URL entry.
    """
    context = RequestContext(request)
    entry = get_object_or_404(m.Entry, id=entry_id)
    if not entry.user == request.user:
        return HttpResponseRedirect('/entry/%s' % entry.id)
    if request.method == 'POST':
        # NOTE: this is pretty redundant.  not completely, but pretty.
        form = UrlEntryForm(request.POST)
        if form.is_valid():
            url_str = form.cleaned_data['url']
            tags_orig = form.cleaned_data['tags']
            entry.title = form.cleaned_data['title']
            entry.is_private = form.cleaned_data['is_private']
            entry.comment = form.cleaned_data['comment']
            entry.content = form.cleaned_data['content']
            
            url, was_created = m.Url.objects.get_or_create(value=url_str)
            entry.url = url
            
            # Remove original tags
            for tag in entry.tags.all():
                entry.tags.remove(tag)
            
            tag_strs = tags_orig.split(' ')
            # Remove repeats
            for tag in tag_strs:
                while tag_strs.count(tag) > 1:
                    tag_strs.remove(tag)
            # Remove empty tags like ''
            tag_strs = [tag for tag in tag_strs if not tag == '']
            # Remove bad tags, for bad chars or too lengthy
            for tag_str in tag_strs:
                if RE_BAD_CHARS.search(tag_str):
                    tag_strs.remove(tag_str)
                elif len(tag_str) > 30:
                    tag_strs.remove(tag_str)
            # Build up and add real tag objects
            for tag_str in tag_strs:
                tag, was_created = m.Tag.objects.get_or_create(name=tag_str)
                entry.tags.add(tag)

            entry.save()

            request.user.message_set.create(message='Saved your entry.')
            #return HttpResponseRedirect('/entry/%s/edit' % entry.id)
            return HttpResponseRedirect('/')
    else:
        data = {
            'url': entry.url.value,
            'title': entry.title,
            'comment': entry.comment,
            'content': entry.content,
            'tags': ' '.join([t.name for t in entry.tags.all()]),
            'is_private': entry.is_private,
            }
        form = UrlEntryForm(data)
    return render_to_response('update_entry.html', 
        {'form': form, 'entry': entry, 'foo': 'foo'}, context)
    

def indexing_js(request):
    """
    Return the base indexing javascript.  Rendered as a template to allow
    settings-based url base value, only.  Ugh.
    """
    t = loader.get_template('indexing.js')
    c = RequestContext(request, {'site_url': settings.UNALOG_URL})
    
    return HttpResponse(t.render(c), mimetype='application/javascript')



def atom_feed(page, **kwargs):
    """
    Simple Atom Syndication Format 1.0 feed.
    """
    title = u'unalog - ' + kwargs.get('title', u'')
    link = kwargs.get('link', u'http://unalog.com/')
    description = kwargs.get('description', u'unalog feed')
    language = kwargs.get('language', u'en')
    feed = feedgenerator.Atom1Feed(title=title, link=link,
        description=description, language=language)
    for entry in page.object_list:
        feed.add_item(title=entry.title, link=entry.url.value, 
            description=entry.comment, pubdate=entry.date_created,
            categories=[tag.name for tag in entry.tags.all()])
    return HttpResponse(feed.writeString('utf8'), 
        mimetype='application/atom+xml')


    
def logout_view(request):
    """
    Log a user out of the system.
    """
    logout(request)
    return HttpResponseRedirect('/')


def register_view(request):
    """
    Register a new user in the system.
    """
    context = RequestContext(request)
    return render_to_response('register.html', 
        {'title': 'Registration disabled'},
        context)


def index(request, format='html'):
    """
    Basic view for everybody.
    """
    context = RequestContext(request)
    qs = standard_entries()
    paginator, page = pagify(request, qs)
    if format == 'atom':
        return atom_feed(page=page, title='latest from everybody')
    return render_to_response('index.html', {
        'view_hidden': True,
        'title': 'home', 
        'paginator': paginator, 'page': page, 
        'view_hidden': False,
        'feed_url': '/feed/',
        }, context)
        
        
def tag(request, tag_name, format='html'):
    """
    Basic view for any tag.
    """
    context = RequestContext(request)
    qs = standard_entries()
    qs = qs.filter(tags__name=tag_name)
    paginator, page = pagify(request, qs)
    if format == 'atom':
        return atom_feed(page=page, title='latest from everybody for tag "%s"' % tag_name,
            link='/tag/%s/' % tag_name)
    return render_to_response('index.html', {
        'title': 'tag "%s" for everyone' % tag_name, 
        'browse_type': 'tag', 'tag': tag_name,
        'paginator': paginator, 'page': page, 
        'feed_url': '/tag/%s/feed/' % tag_name,
        }, context)

def tags_all(request):
    """
    Summary page for overall tag usage.
    """
    context = RequestContext(request)
    qs_count = m.Tag.count()
    count_paginator, count_page = pagify(request, qs_count)
    qs_alpha = m.Tag.count(order='alpha')
    alpha_paginator, alpha_page = pagify(request, qs_alpha)
    return render_to_response('tags.html', {
        'view_hidden': False,
        'title': 'all tags',
        'paginator': count_paginator, 'page': count_page,
        'alpha_paginator': alpha_paginator, 'alpha_page': alpha_page,
        }, context)

        
def person(request, user_name):
    """
    A legacy URL pattern.  Resolve it just in case.
    """
    return HttpResponsePermanentRedirect('/user/%s/' % user_name)


def may_see_user(request_user, entry_user):
    may_see = True
    message = ''
    if entry_user.is_active == False:
        may_see = False
        message = 'User is not active'
    if entry_user.get_profile().is_private:
        if request_user != entry_user:
            may_see = False
            message = "This user's entries are private."
    return (may_see, message)


def user(request, user_name, format='html'):
    """
    Basic view for a user.
    """
    context = RequestContext(request)
    user = get_object_or_404(m.User, username=user_name)
    may_see, message = may_see_user(request.user, user)
    if not may_see:
        return render_to_response('index.html', {
            'view_hidden': True,
            'title': 'user %s' % user_name,
            'message': message,
            }, context)
        
    qs = m.Entry.objects.filter(user=user)
    # Hide public entry_user's private stuff unless it's the user themself
    if user != request.user:
        qs = qs.exclude(is_private=True)
    qs = qs.order_by('-date_created')
    paginator, page = pagify(request, qs)
        
    if format == 'atom':
        return atom_feed(page=page, title='latest from %s' % user_name,
            link='http://unalog.com/user/%s' % user_name)
    return render_to_response('index.html', {
        'view_hidden': False,
        'title': 'user %s' % user_name,
        'paginator': paginator, 'page': page,
        'browse_type': 'user', 'browse_user': user, 
        'browse_user_name': user.username,
        'feed_url': '/user/%s/feed/' % user_name,
        }, context)
    

def user_tag(request, user_name, tag_name='', format='html'):
    """
    View one user's entries with a particular tag.
    """
    context = RequestContext(request)
    user = get_object_or_404(m.User, username=user_name)
    may_see, message = may_see_user(request.user, user)
    if not may_see:
        return render_to_response('index.html', {
            'view_hidden': True,
            'title': 'user %s' % user_name,
            'message': message,
            }, context)

    qs = m.Entry.objects.filter(user=user, tags__name=tag_name)
    # Hide public entry_user's private stuff unless it's the user themself
    if user != request.user:
        qs = qs.exclude(is_private=True)
    qs = qs.order_by('-date_created')
    paginator, page = pagify(request, qs)

    if format == 'atom':
        return atom_feed(page=page, 
            title='latest from %s - "%s"' % (user_name, tag_name),
            link='http://unalog.com/user/%s/tag/%s/' % (user_name, tag_name))
    return render_to_response('index.html', {
        'view_hidden': False,
        'title': "user %s's tag %s" % (user_name, tag_name),
        'paginator': paginator, 'page': page,
        'browse_type': 'tag', 'browse_user': user, 'tag': tag_name,
        'feed_url': '/user/%s/tag/%s/feed/' % (user_name, tag_name),
        }, context)
    
    
def user_tags(request, user_name):
    """
    Review all this user's tags.
    """
    context = RequestContext(request)
    user = get_object_or_404(m.User, username=user_name)
    may_see, message = may_see_user(request.user, user)
    if not may_see:
        return render_to_response('index.html', {
            'view_hidden': True,
            'title': 'user %s' % user_name,
            'message': message,
            }, context)
    
    qs = m.Tag.count(user=user, request_user=request.user)
    paginator, page = pagify(request, qs)
    
    return render_to_response('tags.html', {
        'view_hidden': False,
        'title': "user %s's tags" % user_name,
        'paginator': paginator, 'page': page,
        'browse_user': user,
        }, context)


def url_all(request, md5sum='', format='html'):
    """
    Review all entries from all users for this one URL.
    """
    context = RequestContext(request)
    url = get_object_or_404(m.Url, md5sum=md5sum)
    qs = standard_entries()
    qs = qs.filter(url=url)
    paginator, page = pagify(request, qs)
    if format == 'atom':
        return atom_feed(page=page, title='latest for url',
            link='http://unalog.com/url/%s/' % md5sum)
    return render_to_response('index.html', {
        'view_hidden': False,
        'title': "url %s" % url.value[:50],
        'paginator': paginator, 'page': page,
        'browse_type': 'url', 'browse_url': url,
        'feed_url': '/url/%s/feed/' % md5sum,
        }, context)

    
# Groups.

def may_see_group(request_user, group):
    may_see = True
    message = ''
    if group.get_profile().is_private:
        if not request_user in group.user_set.all():
            may_see = False
            message = "This group's entries are private."
    print 'may_see:', may_see, 'message:', message
    return (may_see, message)

    
def group(request, group_name, format='html'):
    """
    Basic view for a group.
    """
    context = RequestContext(request)
    group = get_object_or_404(m.Group, name=group_name)
    may_see, message = may_see_group(request.user, group)
    
    if not may_see:
        return render_to_response('index.html', {
            'view_hidden': True,
            'title': 'group %s' % group_name,
            'message': message,
            }, context)
    
    qs = m.Entry.objects.filter(groups__name=group_name)
    qs = qs.order_by('-date_created')
    # If they're not a member, don't let them see private stuff
    if not request.user in group.user_set.all():
        qs.exclude(is_private=True)
    paginator, page = pagify(request, qs)
    if format == 'atom':
        return atom_feed(page=page, title='latest from group "%s"' % group_name,
            link='http://unalog.com/group/%s/' % group_name)
    return render_to_response('index.html', {
        'view_hidden': False,
        'title': 'Group %s' % group_name,
        'paginator': paginator, 'page': page,
        'browse_type': 'group', 'browse_group': group, 
        'feed_url': '/group/%s/feed/' % group_name,
        }, context)
    
def group_tag(request, group_name, tag_name='', format='html'):
    """
    View one group's entries with a particular tag.
    """
    context = RequestContext(request)
    group = get_object_or_404(m.Group, name=group_name)
    may_see, message = may_see_group(request.user, group)
    
    if not may_see:
        return render_to_response('index.html', {
            'view_hidden': True,
            'title': 'group %s' % group_name,
            'message': message,
            }, context)
    
    qs = m.Entry.objects.filter(groups__name=group_name, tags__name=tag_name)
    qs = qs.order_by('-date_created')
    # If they're not a member, don't let them see private stuff
    if not request.user in group.user_set.all():
        qs.exclude(is_private=True)
    paginator, page = pagify(request, qs)
    if format == 'atom':
        return atom_feed(page=page, 
            title='latest from group "%s" tag "%s"' % (group_name, tag_name),
            link='http://unalog.com/group/%s/tag/%s/' % (group_name, tag_name))
    return render_to_response('index.html', {
        'view_hidden': False,
        'title': "Group %s's tag %s" % (group_name, tag_name),
        'paginator': paginator, 'page': page,
        'browse_type': 'group', 'browse_group': group, 'tag': tag_name,
        'feed_url': '/group/%s/tag/%s/feed/' % (group_name, tag_name),
        }, context)
        
        
COMMON_FACET_PARAMS = {
    'facet': 'true',
    'facet.field': 'tag',
    'facet.mincount': 2,
    }        



def solr_connection():
    s = SolrConnection(settings.SOLR_URL)
    return s


class SolrPaginator:
    """
    Take a solr.py result and return a Django paginator-like object.
    """
    
    def __init__(self, q, result):
        self.q = q
        self.result = result
        
    @property
    def count(self):
        return int(self.result.numFound)

    @property
    def num_pages(self):
        if self.count == 0:
            return 0
        real_num = (self.count * 1.0) / len(self.result.results)
        return int(math.ceil(real_num))
            
    @property
    def page_range(self):
        """List the index numbers of the available result pages."""
        if self.count == 0:
            return []
        # Add one because range is right-side exclusive
        return range(1, self.num_pages + 1)

    def _fetch_page(self, start=0):
        """Retrieve a new result response from Solr."""
        s = solr_connection()
        new_results = s.query(self.q, start=start)
        return new_results
        
    def page(self, page_num=1):
        """Return the requested Page object"""
        try:
            int(page_num)
        except:
            raise 'PageNotAnInteger'
        
        if page_num not in self.page_range:
            raise 'EmptyPage', 'That page does not exist.'

        # Page 1 starts at 0; take one off before calculating
        start = (page_num - 1) * len(self.result.results)
        new_result = self._fetch_page(start=start)
        return SolrPage(new_result.results, page_num, self)
    

class SolrPage:
    """A single Paginator-style page."""
    
    def __init__(self, result, page_num, paginator):
        self.result = result
        self.number = page_num
        self.paginator = paginator
        
    @property
    def object_list(self):
        qs = m.Entry.objects.filter(id__in=[r['id'] for r in self.result])
        return qs
    
    def has_next(self):
        if self.number < self.paginator.num_pages:
            return True
        return False
            
    def has_previous(self):
        if self.number > 1:
            return True
        return False
            
    def has_other_pages(self):
        if self.paginator.num_pages > 1:
            return True
        return False
    
    def start_index(self):
        # off by one because self.number is 1-based w/django,
        # but start is 0-based in solr 
        return (self.number - 1) * len(self.result)
        
    def end_index(self):
        # off by one because we want the last one in this set, 
        # not the next after that, to match django paginator
        return self.start_index() + len(self.result) - 1
        
    def next_page_number(self):
        return self.number + 1
            
    def previous_page_number(self):
        return self.number - 1
    
        
        
def search(request):
    """
    Simple search, queries Solr behind the scenes.
    
    FIXME: a QueryConstraints.to_solr() please
    """
    context = RequestContext(request)
    q = request.GET.get('q', '')
    if q:
        s = SolrConnection(settings.SOLR_URL)
        r = s.query(q, rows=25, **COMMON_FACET_PARAMS)
        paginator = SolrPaginator(q, r)
        try:
            page = get_page(request, paginator)
        except:
            page = None
        return render_to_response('index.html', {
            'q': q,
            'title': 'Search for "%s"' % q,
            'paginator': paginator, 'page': page,
            'query_param': 'q=%s&' % q,
            }, context)
    return render_to_response('index.html', context)