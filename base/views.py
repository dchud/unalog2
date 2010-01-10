import math
import re

from django.conf import settings
from django.contrib.auth import authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import login
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django import forms
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.http import HttpResponsePermanentRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, loader
from django.utils import feedgenerator
from solr import SolrConnection

from unalog2.base import models as m
from unalog2.settings import SOLR_URL

class EntryForm (forms.Form):
    url = forms.URLField(required=True, label='URL')
    title = forms.CharField(required=True)
    tags = forms.CharField(required=False, help_text='Separate with spaces')
    is_private = forms.BooleanField(required=False)
    comment = forms.CharField(required=False, widget=forms.Textarea)
    content = forms.CharField(required=False, widget=forms.Textarea)


def standard_entries ():
    """
    Start a base queryset of entries common to many pages.
    """
    qs = m.Entry.objects.exclude(user__is_active=False)
    # Note:  on the following, qs.exclude...=True blows up.
    qs = qs.filter(user__userprofile__is_private=False)
    qs = qs.exclude(is_private=True)
    qs = qs.order_by('-date_created')
    return qs


def constrained_entries (request, requested_user=None,
    requested_group=None, tag_name=None):
    """
    Start a base queryset of entries common to many pages.
    """
    qs = m.Entry.objects.exclude(user__is_active=False)
    
    if request.user:
        if requested_group:
            pass
        if request.user != requested_user:
            # Non-private users
            # Note:  on the following, qs.exclude...=True blows up.
            qs = qs.filter(user__userprofile__is_private=False)
            # Non-private entries
            qs = qs.exclude(is_private=True)
        else:
            # They're asking for their own entries, so let 'em through
            pass
            
        # Apply filters
        for f in request.user.filters.filter(is_active=True):
            if f.attr_name == 'user':
                if f.is_exact:
                    qs = qs.exclude(user__username=f.value)
                else:
                    qs = qs.exclude(user__username__icontains=f.value)
            elif f.attr_name == 'tag':
                if f.is_exact:
                    qs = qs.exclude(tags__tag__name=f.value)
                else:
                    qs = qs.exclude(tags__tag__name__icontains=f.value)
            elif f.attr_name == 'url':
                if f.is_exact:
                    qs = qs.exclude(url__value=f.value)
                else:
                    qs = qs.exclude(url__value__icontains=f.value)
            
    if tag_name:
        qs = qs.filter(tags__tag__name=tag_name)
    qs = qs.order_by('-date_created')
    return qs



def solr_connection ():
    s = SolrConnection(settings.SOLR_URL)
    return s


def get_page (request, paginator):
    try:
        page_num = int(request.GET.get('p', '1'))
        if page_num not in paginator.page_range:
            raise ValueError, 'Invalid page number'
    except ValueError:
        page_num = 1
    return paginator.page(page_num)
    

def pagify (request, qs, num_items=50):
    """
    Convenience helper to paginate out a query set.
    """
    try:
        num_items = int(num_items)
    except:
        num_items = 50
    paginator = Paginator(qs, num_items)
    page = get_page(request, paginator)
    return paginator, page


def old_stack_link (request):
    """
    Redirect from old bookmarklet path.
    """
    return HttpResponseRedirect(reverse('entry_new'))
    

@login_required
def entry_new (request):
    """
    Save a new URL entry.
    """
    context = RequestContext(request)
    d = {}
    if request.method == 'POST':
        form = EntryForm(request.POST)
        if form.is_valid():
            url_str = form.cleaned_data['url']
            title = form.cleaned_data['title']
            is_private = form.cleaned_data['is_private']
            tags_orig = form.cleaned_data['tags']
            comment = form.cleaned_data['comment']
            content = form.cleaned_data['content']
            submit = request.POST.get('submit', None)
            
            # Maybe they saved this one before?  Check by url
            old_entries = m.Entry.objects.filter(user=request.user, 
                url__value=url_str)
            if old_entries:
                # If it's not 'Save anyway', they haven't confirmed yet
                if not submit == 'Save anyway':
                    return render_to_response('entry_new.html', {
                        'form': form,
                        'old_entries': old_entries,
                        }, context)
            
            # It must be either new, or a duplicate url by choice, so go ahead
            new_entry = m.Entry(user=request.user, title=title, 
                is_private=is_private, comment=comment, content=content)

            url, was_created = m.Url.objects.get_or_create(value=url_str)
            new_entry.url = url
            
            # Save that sucker before adding many-to-manys
            new_entry.save()

            tag_strs = tags_orig.split(' ')
            new_entry.add_tags(tag_strs)

            request.user.message_set.create(message='Saved your entry.')
            # If they had to confirm this, they don't need an edit screen again
            if submit == 'Save anyway':
                return HttpResponseRedirect(reverse('index'))
            # Otherwise, let them tweak it
            return HttpResponseRedirect(reverse('entry_edit', args=[new_entry.id]))
    else:
        form = EntryForm()
    return render_to_response('entry_new.html', 
        {'form': form}, context)


@login_required
def entry_delete (request, entry_id):
    """
    Let a user choose to delete an entry.
    """
    context = RequestContext(request)
    e = get_object_or_404(m.Entry, id=entry_id)
    if e.user != request.user:
        request.user.message_set.create(
            message="You can't go and delete other people's stuff like that, dude.")
        return HttpRequestRedirect(reverse('index'))
    if request.method == 'POST':
        was_confirmed = request.POST['submit']
        if was_confirmed == 'yes':
            e.delete()
            message = 'Deleted entry %s' % entry_id
            request.user.message_set.create(message=message)
            return HttpResponseRedirect(reverse('index'))
    return render_to_response('delete_entry.html', 
        {'entry': e}, context)


def entry (request, entry_id):
    """
    View an existing entry.
    """
    context = RequestContext(request)
    e = get_object_or_404(m.Entry, id=entry_id)
    return render_to_response('url_entry.html', {'entry': e}, context)


@login_required
def entry_edit (request, entry_id):
    context = RequestContext(request)
    e = get_object_or_404(m.Entry, id=entry_id)
    if not e.user == request.user:
        return HttpResponseRedirect(reverse('entry', args=[e.id]))
    if request.method == 'POST':
        # NOTE: this is pretty redundant.  not completely, but pretty.
        form = EntryForm(request.POST)
        if form.is_valid():
            url_str = form.cleaned_data['url']
            tags_orig = form.cleaned_data['tags']
            e.title = form.cleaned_data['title']
            e.is_private = form.cleaned_data['is_private']
            e.comment = form.cleaned_data['comment']
            e.content = form.cleaned_data['content']
            
            url, was_created = m.Url.objects.get_or_create(value=url_str)
            e.url = url
            
            # Remove original tags
            m.EntryTag.objects.filter(entry=e).delete()
            
            tag_strs = tags_orig.split(' ')
            e.add_tags(tag_strs)

            e.save()

            request.user.message_set.create(message='Saved your entry.')
            return HttpResponseRedirect(reverse('index'))
    else:
        data = {
            'url': e.url.value,
            'title': e.title,
            'comment': e.comment,
            'content': e.content,
            'tags': ' '.join([et.tag.name for et in e.tags.all()]),
            'is_private': e.is_private,
            }
        form = EntryForm(data)
    return render_to_response('update_entry.html', {
        'form': form, 'entry': e,
        }, context)
    

def bookmarklet (request):
    context = RequestContext(request)
    return render_to_response('bookmarklet.html', {
        'site_url': settings.UNALOG_URL,
        }, context)


def indexing_js (request):
    """
    Return the base indexing javascript.  Rendered as a template to allow
    settings-based url base value, only.  Ugh.
    """
    t = loader.get_template('indexing.js')
    context = RequestContext(request, {'site_url': settings.UNALOG_URL})
    return HttpResponse(t.render(context), mimetype='application/javascript')



def atom_feed (page, **kwargs):
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
            id=reverse('entry', args=[entry.id]),
            description=entry.comment, pubdate=entry.date_created,
            categories=[entry_tag.tag.name for entry_tag in entry.tags.all()])
    return HttpResponse(feed.writeString('utf8'), 
        mimetype='application/xml')


def about (request):
    context = RequestContext(request)
    return render_to_response('about.html', 
        {'title': 'About'},
        context)

def contact (request):
    context = RequestContext(request)
    return render_to_response('contact.html', 
        {'title': 'Contact'},
        context)

def logout_view (request):
    logout(request)
    return HttpResponseRedirect('/')

def register_view (request):
    context = RequestContext(request)
    return render_to_response('register.html', 
        {'title': 'Registration disabled'},
        context)


def index (request):
    context = RequestContext(request)
    qs = constrained_entries(request)
    paginator, page = pagify(request, qs)
    return render_to_response('index.html', {
        'title': 'home', 
        'paginator': paginator, 'page': page, 
        'feed_url': reverse('feed_atom'),
        }, context)


def feed_atom (request):
    context = RequestContext(request)
    qs = constrained_entries(request)
    paginator, page = pagify(request, qs)
    return atom_feed(page=page, title='latest from everybody')

        
def tag (request, tag_name):
    context = RequestContext(request)
    qs = constrained_entries(request, tag_name=tag_name)
    paginator, page = pagify(request, qs)
    return render_to_response('index.html', {
        'browse_type': 'tag', 'tag': tag_name,
        'paginator': paginator, 'page': page, 
        'feed_url': reverse('tag_atom', args=[tag_name]),
        }, context)


def tag_atom (request, tag_name):
    context = RequestContext(request)
    qs = constrained_entries(request, tag_name=tag_name)
    paginator, page = pagify(request, qs)
    return atom_feed(page=page, 
        title='latest from everybody for tag "%s"' % tag_name,
        link=reverse('tag', args=[tag_name]))


def tags (request):
    context = RequestContext(request)
    qs_count = m.EntryTag.count()
    count_paginator, count_page = pagify(request, qs_count)
    qs_alpha = m.EntryTag.count(order='alpha')
    alpha_paginator, alpha_page = pagify(request, qs_alpha)
    return render_to_response('tags.html', {
        'paginator': count_paginator, 'page': count_page,
        'alpha_paginator': alpha_paginator, 'alpha_page': alpha_page,
        }, context)

        
def may_see_user (request_user, entry_user):
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


def person (request, user_name):
    """A legacy URL pattern.  Resolve it just in case."""
    return HttpResponsePermanentRedirect(reverse('user', args=[user_name]))


def user (request, user_name):
    context = RequestContext(request)
    u = get_object_or_404(m.User, username=user_name)
    may_see, message = may_see_user(request.user, u)
    if not may_see:
        return render_to_response('index.html', {
            'message': message,
            }, context)
        
    qs = m.Entry.objects.filter(user=u)
    # Hide public entry_user's private stuff unless it's the user themself
    if u != request.user:
        qs = qs.exclude(is_private=True)
    qs = qs.order_by('-date_created')
    paginator, page = pagify(request, qs)
    return render_to_response('index.html', {
        'paginator': paginator, 'page': page,
        'browse_type': 'user', 'browse_user': u, 
        'browse_user_name': u.username,
        'feed_url': reverse('user_atom', args=[user_name]),
        }, context)
    

def user_atom (request, user_name):
    context = RequestContext(request)
    u = get_object_or_404(m.User, username=user_name)
    may_see, message = may_see_user(request.user, u)
    if not may_see:
        return render_to_response('index.html', {
            'title': 'user %s' % user_name,
            'message': message,
            }, context)

    qs = m.Entry.objects.filter(user=u)
    # Hide public entry_user's private stuff unless it's the user themself
    if u != request.user:
        qs = qs.exclude(is_private=True)
    qs = qs.order_by('-date_created')
    paginator, page = pagify(request, qs)

    return atom_feed(page=page, title='latest from %s' % user_name,
        link=reverse('user_atom', args=[user_name]))


def user_tag (request, user_name, tag_name=''):
    context = RequestContext(request)
    u = get_object_or_404(m.User, username=user_name)
    may_see, message = may_see_user(request.user, u)
    if not may_see:
        return render_to_response('index.html', {
            'message': message,
            }, context)

    qs = m.Entry.objects.filter(user=u, tags__tag__name=tag_name)
    # Hide public entry_user's private stuff unless it's the user themself
    if u != request.user:
        qs = qs.exclude(is_private=True)
    qs = qs.order_by('-date_created')
    paginator, page = pagify(request, qs)
    return render_to_response('index.html', {
        'paginator': paginator, 'page': page,
        'browse_type': 'tag', 'browse_user': u, 'tag': tag_name,
        'feed_url': reverse('user_tag_atom', args=[user_name, tag_name]),
        }, context)


def user_tag_atom (request, user_name, tag_name=''):
    context = RequestContext(request)
    u = get_object_or_404(m.User, username=user_name)
    may_see, message = may_see_user(request.user, u)
    if not may_see:
        return render_to_response('index.html', {
            'title': 'user %s' % user_name,
            'message': message,
            }, context)

    qs = m.Entry.objects.filter(user=u, tags__tag__name=tag_name)
    # Hide public entry_user's private stuff unless it's the user themself
    if u != request.user:
        qs = qs.exclude(is_private=True)
    qs = qs.order_by('-date_created')
    paginator, page = pagify(request, qs)

    return atom_feed(page=page, 
        title='latest from %s - "%s"' % (user_name, tag_name),
        link=reverse('user_tag', args=[user_name, tag_name]))
    
    
def user_tags (request, user_name):
    """
    Review all this user's tags.
    """
    context = RequestContext(request)
    u = get_object_or_404(m.User, username=user_name)
    may_see, message = may_see_user(request.user, u)
    if not may_see:
        return render_to_response('index.html', {
            'message': message,
            }, context)
    
    qs = m.EntryTag.count(user=u, request_user=request.user)
    paginator, page = pagify(request, qs, num_items=250)
    qs_alpha = m.EntryTag.count(order='alpha')
    alpha_paginator, alpha_page = pagify(request, qs_alpha, num_items=250)
    
    return render_to_response('tags.html', {
        'paginator': paginator, 'page': page,
        'alpha_paginator': alpha_paginator, 'alpha_page': alpha_page,
        'browse_user': u,
        }, context)


def url (request, md5sum=''):
    """
    Review all entries from all users for this one URL.
    """
    context = RequestContext(request)
    url = get_object_or_404(m.Url, md5sum=md5sum)
    qs = standard_entries()
    qs = qs.filter(url=url)
    paginator, page = pagify(request, qs)
    return render_to_response('index.html', {
        'view_hidden': False,
        'title': "url %s" % url.value[:50],
        'paginator': paginator, 'page': page,
        'browse_type': 'url', 'browse_url': url,
        'feed_url': reverse('url_atom', args=[md5sum]),
        }, context)

def url_atom (request):
    """
    Review all entries from all users for this one URL.
    """
    context = RequestContext(request)
    url = get_object_or_404(m.Url, md5sum=md5sum)
    qs = standard_entries()
    qs = qs.filter(url=url)
    paginator, page = pagify(request, qs)
    return atom_feed(page=page, title='latest for url',
        link=reverse(url('url', args=[md5sum])))

    
# Groups.

def may_see_group (request_user, group):
    may_see = True
    message = ''
    if group.get_profile().is_private:
        if not request_user in group.user_set.all():
            may_see = False
            message = "This group's entries are private."
    print 'may_see:', may_see, 'message:', message
    return (may_see, message)

    
def group (request, group_name, format='html'):
    """
    Basic view for a group.
    """
    context = RequestContext(request)
    group = get_object_or_404(m.Group, name=group_name)
    may_see, message = may_see_group(request.user, group)
    
    if not may_see:
        return render_to_response('index.html', {
            'view_hidden': True,
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
        'paginator': paginator, 'page': page,
        'browse_type': 'group', 'browse_group': group, 
        'feed_url': reverse('group_atom', args=[group_name]),
        }, context)
    
def group_tag (request, group_name, tag_name=''):
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
    qs = m.Entry.objects.filter(groups__name=group_name, tags__tag__name=tag_name)
    qs = qs.order_by('-date_created')
    # If they're not a member, don't let them see private stuff
    if not request.user in group.user_set.all():
        qs.exclude(is_private=True)
    paginator, page = pagify(request, qs)
    return render_to_response('index.html', {
        'title': "Group %s's tag %s" % (group_name, tag_name),
        'paginator': paginator, 'page': page,
        'browse_type': 'group', 'browse_group': group, 'tag': tag_name,
        'feed_url': reverse('group_tag_atom', args=[group_name, tag_name]),
        }, context)
        
def group_tag_atom (request, group_name):
    context = RequestContext(request)
    group = get_object_or_404(m.Group, name=group_name)
    may_see, message = may_see_group(request.user, group)
    if not may_see:
        return render_to_response('index.html', {
            'title': 'group %s' % group_name,
            'message': message,
            }, context)
    qs = m.Entry.objects.filter(groups__name=group_name, tags__tag__name=tag_name)
    qs = qs.order_by('-date_created')
    # If they're not a member, don't let them see private stuff
    if not request.user in group.user_set.all():
        qs.exclude(is_private=True)
    paginator, page = pagify(request, qs)
    return atom_feed(page=page, 
        title='latest from group "%s" tag "%s"' % (group_name, tag_name),
        link=reverse('group_tag_atom', args=[group_name, tag_name]))


        
COMMON_FACET_PARAMS = {
    'facet': 'true',
    'facet.field': 'tag',
    'facet.mincount': 2,
    }        


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
    
        
        
def search (request):
    """
    Simple search, queries Solr behind the scenes.
    
    FIXME: a QueryConstraints.to_solr() please
    """
    context = RequestContext(request)
    q = request.GET.get('q', '')
    if q:
        s = solr_connection()
        r = s.query(q, rows=50, sort='date_created', sort_order='asc',
            **COMMON_FACET_PARAMS)
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
