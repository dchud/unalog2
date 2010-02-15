import math
import re

from django.conf import settings
from django.contrib.auth import authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import login
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.db.models import Count
from django import forms
from django.forms.models import modelformset_factory
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.http import HttpResponsePermanentRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, loader
from django.utils import feedgenerator

import solr

from basicauth import logged_in_or_basicauth

from base import models as m
from settings import REALM, SOLR_URL


class EntryForm (forms.Form):
    url = forms.URLField(required=True, label='URL')
    title = forms.CharField(required=True)
    tags = forms.CharField(required=False, help_text='Separate with spaces')
    is_private = forms.BooleanField(required=False)
    comment = forms.CharField(required=False, widget=forms.Textarea)
    content = forms.CharField(required=False, widget=forms.Textarea)


def apply_user_filters_to_entries (request, qs):
    # Assume the user's already been authenticated.
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
    return qs


def apply_user_filters_to_entry_tags (request, qs):
    # Assume the user's already been authenticated.
    # FIXME: DRY.
    for f in request.user.filters.filter(is_active=True):
        if f.attr_name == 'user':
            if f.is_exact:
                qs = qs.exclude(entry__user__username=f.value)
            else:
                qs = qs.exclude(entry__user__username__icontains=f.value)
        elif f.attr_name == 'tag':
            if f.is_exact:
                qs = qs.exclude(entry__tags__tag__name=f.value)
            else:
                qs = qs.exclude(entry__tags__tag__name__icontains=f.value)
        elif f.attr_name == 'url':
            if f.is_exact:
                qs = qs.exclude(entry__url__value=f.value)
            else:
                qs = qs.exclude(entry__url__value__icontains=f.value)
    return qs


def constrained_entries (request, requested_user=None, requested_group=None, 
    tag=None, candidate_ids=[]):
    """
    Start a base queryset of entries common to many pages.
    """
    # Never show entries from inactive user accounts.
    qs = m.Entry.objects.exclude(user__is_active=False)

    # Not sure we need this, but just in case.
    if candidate_ids:
        qs = qs.filter(id__in=candidate_ids)
        
    # Unless this gets set to false, we'll limit private users and entries.
    add_standard_restrictions = True

    # /group/ and /user/ requests are mutually exclusive.
    if requested_group:
        if requested_group.get_profile().is_private:
            # If they're a member, let them see private stuff
            if request.user in requested_group.user_set.all():
                add_standard_restrictions = False
            else:
                # Since they're not, don't let them see anything
                qs = qs.exclude(groups__name=requested_group.name)
        qs = qs.filter(groups__name=requested_group.name)
    elif requested_user:
        if requested_user == request.user:
            add_standard_restrictions = False
        qs = qs.filter(user=requested_user)

    if add_standard_restrictions:
        qs = qs.exclude(is_private=True)
        # Note:  on the following, qs.exclude...=True blows up.
        qs = qs.filter(user__userprofile__is_private=False)

    # limit to this tag
    if tag:
        qs = qs.filter(tags__tag__name=tag.name)

    # apply filters for logged-in users
    if request.user.is_authenticated():
        qs = apply_user_filters_to_entries(request, qs)

    qs = qs.order_by('-date_created')
    return qs


# Hmm, what's the best way to do this?  Punt for now and do 
# something simple.
SOLR_CONNECTION = solr.SolrConnection(settings.SOLR_URL)

def solr_connection ():
    return SOLR_CONNECTION


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


@logged_in_or_basicauth(REALM)
def entry_new (request):
    """
    Save a new URL entry.
    """
    request.encoding = 'utf-8'
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
            new_entry.add_tags(tags_orig)

            request.user.message_set.create(message='Saved!')
            # If they had to confirm this, they don't need an edit screen again
            if submit == 'Save anyway':
                return HttpResponseRedirect(reverse('index'))
            # Otherwise, let them tweak it
            return HttpResponseRedirect(reverse('entry_edit', args=[new_entry.id]))
    else:
        form = EntryForm()
    return render_to_response('entry_new.html', 
        {'form': form}, context)


@logged_in_or_basicauth(REALM)
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
    return render_to_response('entry_delete.html', 
        {'entry': e}, context)


def entry (request, entry_id):
    """
    View an existing entry.
    """
    context = RequestContext(request)
    # First use the shortcut to bounce to 404 if nec.; a cheat!
    e = get_object_or_404(m.Entry, id=entry_id)
    qs = constrained_entries(request, candidate_ids=[entry_id])
    return render_to_response('index.html', {
        'title': 'Entry', 
        'paginator': paginator, 'page': page, 
        }, context)


@logged_in_or_basicauth(REALM)
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
            
            e.add_tags(tags_orig)
            e.save()
            
            request.user.message_set.create(message='Updated!')
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
    return render_to_response('entry_edit.html', {
        'form': form, 'entry': e,
        }, context)


def bookmarklet (request):
    context = RequestContext(request)
    return render_to_response('bookmarklet.html', {
        'site_url': settings.UNALOG_URL,
        'title': 'bookmarklets',
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
    return HttpResponseRedirect(reverse('index'))

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
        'feed_url': reverse('feed'),
        }, context)


def feed (request):
    context = RequestContext(request)
    qs = constrained_entries(request)
    paginator, page = pagify(request, qs)
    return atom_feed(page=page, title='latest from everybody')

        
def tag (request, tag_name):
    context = RequestContext(request)
    t = get_object_or_404(m.Tag, name=tag_name)
    qs = constrained_entries(request, tag=t)
    paginator, page = pagify(request, qs)
    return render_to_response('index.html', {
        'browse_type': 'tag', 'tag': t,
        'paginator': paginator, 'page': page, 
        'feed_url': reverse('tag_feed', args=[tag_name]),
        }, context)


def tag_feed (request, tag_name):
    context = RequestContext(request)
    t = get_object_or_404(m.Tag, name=tag_name)
    qs = constrained_entries(request, tag=t)
    paginator, page = pagify(request, qs)
    return atom_feed(page=page, 
        title='latest from everybody for tag "%s"' % tag_name,
        link=reverse('tag', args=[tag_name]))


def tags (request):
    context = RequestContext(request)
    qs = m.EntryTag.objects.filter(entry__user__userprofile__is_private=False)
    qs = qs.exclude(entry__is_private=True)
    if request.user.is_authenticated():
        qs = apply_user_filters_to_entry_tags(request, qs)
    qs = qs.values('tag__name').annotate(Count('tag'))
    qs_count = qs.order_by('-tag__count')
    count_paginator, count_page = pagify(request, qs_count)
    qs_alpha = qs.order_by('tag__name')
    alpha_paginator, alpha_page = pagify(request, qs_alpha)
    return render_to_response('tags.html', {
        'paginator': count_paginator, 'page': count_page,
        'alpha_paginator': alpha_paginator, 'alpha_page': alpha_page,
        }, context)

        
def person (request, user_name):
    """A legacy URL pattern.  Resolve it just in case."""
    return HttpResponsePermanentRedirect(reverse('user', args=[user_name]))


def may_see_user (request, entry_user):
    may_see = True
    message = ''
    if entry_user.is_active == False:
        may_see = False
        message = 'User is not active'
    if entry_user.get_profile().is_private:
        if request.user != entry_user:
            may_see = False
            message = "This user's entries are private."
    return (may_see, message)


def user (request, user_name):
    context = RequestContext(request)
    u = get_object_or_404(m.User, username=user_name)
    qs = constrained_entries(request, requested_user=u)
    paginator, page = pagify(request, qs)
    return render_to_response('index.html', {
        'paginator': paginator, 'page': page,
        'browse_type': 'user', 'browse_user': u, 
        'browse_user_name': u.username,
        'feed_url': reverse('user_feed', args=[user_name]),
        }, context)
    

def user_feed (request, user_name):
    context = RequestContext(request)
    u = get_object_or_404(m.User, username=user_name)
    qs = constrained_entries(request, requested_user=u)
    paginator, page = pagify(request, qs)
    return atom_feed(page=page, title='latest from %s' % user_name,
        link=reverse('user_feed', args=[user_name]))


def user_tag (request, user_name, tag_name=''):
    context = RequestContext(request)
    u = get_object_or_404(m.User, username=user_name)
    t = get_object_or_404(m.Tag, name=tag_name)
    qs = constrained_entries(request, requested_user=u, tag=t)
    paginator, page = pagify(request, qs)
    return render_to_response('index.html', {
        'paginator': paginator, 'page': page,
        'browse_type': 'tag', 'browse_user': u, 'tag': t,
        'feed_url': reverse('user_tag_feed', args=[user_name, tag_name]),
        }, context)


def user_tag_feed (request, user_name, tag_name=''):
    context = RequestContext(request)
    u = get_object_or_404(m.User, username=user_name)
    t = get_object_or_404(m.Tag, name=tag_name)
    qs = constrained_entries(request, requested_user=u, tag=t)
    paginator, page = pagify(request, qs)
    return atom_feed(page=page, 
        title='latest from %s - tag "%s"' % (user_name, tag.name),
        link=reverse('user_tag', args=[user_name, tag_name]))
    
    
def user_tags (request, user_name):
    context = RequestContext(request)
    u = get_object_or_404(m.User, username=user_name)
    # Er, leave this in here, now, not sure of the cleaner way to handle yet.
    may_see, message = may_see_user(request, u)
    if not may_see:
        return render_to_response('index.html', {
            'message': message,
            }, context)
    qs = m.EntryTag.objects.filter(entry__user=u)
    if request.user != u:
        qs = qs.exclude(entry__is_private=True)
        # I *think* we should do this here. You might be interested in some other
        # user's tags on stuff that you haven't filtered out, right?
        if request.user.is_authenticated():
            qs = apply_user_filters_to_entry_tags(request, qs)
    qs = qs.values('tag__name').annotate(Count('tag'))
    qs_count = qs.order_by('-tag__count')
    count_paginator, count_page = pagify(request, qs_count)
    qs_alpha = qs.order_by('tag__name')
    alpha_paginator, alpha_page = pagify(request, qs_alpha)
    return render_to_response('tags.html', {
        'paginator': count_paginator, 'page': count_page, 'browse_user': u, 
        'alpha_paginator': alpha_paginator, 'alpha_page': alpha_page,
        }, context)


@logged_in_or_basicauth(REALM)
def filter_index (request):
    context = RequestContext(request)
    qs = m.Filter.objects.filter(user=request.user).order_by('date_created')
    FilterFormSet = modelformset_factory(m.Filter, extra=0, can_delete=True)
    if request.method == 'POST':
        formset = FilterFormSet(request.POST, request.FILES)
        if formset.is_valid():
            formset.save()
            request.user.message_set.create(message='Updated your filters.')
        else:
            request.user.message_set.create(message='Please check again.')
    # Generate a new formset no matter what; something might've been deleted.
    formset = FilterFormSet(queryset=qs)
    return render_to_response('filters.html', {
        'formset': formset,
        'new_form': m.FilterForm(instance=m.Filter(user=request.user)),
        'title': 'your filters',
        }, context)
    
    
@logged_in_or_basicauth(REALM)
def filter_new (request):
    context = RequestContext(request)
    if request.method == 'POST':
        form = m.FilterForm(request.POST)
        if form.is_valid():
            form.save()
            request.user.message_set.create(message='Saved your new filter.')
        else:
            request.user.message_set.create(message='Something went wrong, please try again.')
    return HttpResponseRedirect(reverse('filter_index'))
    
    
def url (request, md5sum=''):
    context = RequestContext(request)
    url = get_object_or_404(m.Url, md5sum=md5sum)
    qs = constrained_entries(request)
    qs = qs.filter(url=url)
    paginator, page = pagify(request, qs)
    return render_to_response('index.html', {
        'view_hidden': False,
        'paginator': paginator, 'page': page,
        'browse_type': 'url', 'browse_url': url,
        'feed_url': reverse('url_feed', args=[md5sum]),
        }, context)


def url_feed (request, md5sum=''):
    context = RequestContext(request)
    u = get_object_or_404(m.Url, md5sum=md5sum)
    qs = constrained_entries(request)
    qs = qs.filter(url=u)
    paginator, page = pagify(request, qs)
    return atom_feed(page=page, title='latest for url',
        link=reverse('url', args=[md5sum]))

    
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

    
def group (request, group_name=''):
    context = RequestContext(request)
    g = get_object_or_404(m.Group, name=group_name)
    qs = constrained_entries(request, requested_group=g)
    paginator, page = pagify(request, qs)
    return render_to_response('index.html', {
        'paginator': paginator, 'page': page,
        'browse_type': 'group', 'browse_group': g, 
        'feed_url': reverse('group_feed', args=[group_name]),
        }, context)
        
        
def group_feed (request, group_name=''):
    context = RequestContext(request)
    g = get_object_or_404(m.Group, name=group_name)
    qs = constrained_entries(request, requested_group=g)
    paginator, page = pagify(request, qs)
    return atom_feed(page=page, title='latest from group "%s"' % group_name,
        link=reverse('group', args=[group_name]))
    
    
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
        'feed_url': reverse('group_tag_feed', args=[group_name, tag_name]),
        }, context)
        
def group_tag_feed (request, group_name):
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
        link=reverse('group_tag_feed', args=[group_name, tag_name]))


        
COMMON_FACET_PARAMS = {
    'facet': 'true',
    'facet.field': 'tag',
    'facet.mincount': 2,
    }        


        
def _fill_out_query (request, q=''):
    # always encode first
    full_query = q.encode('utf8') 
    # don't show inactive user entries
    full_query += ' is_active_user:true'
    # check for logged-in user's own entries in case they're private
    if request.user.is_authenticated():
        full_query += ' (user:%s OR (is_private_entry:false AND is_private_user:false))' \
            % request.user.username
    else:
        full_query += ' (is_private_entry:false AND is_private_user:false)'
    return full_query
        
        
def search (request):
    request.encoding = 'utf-8'
    context = RequestContext(request)
    q = request.GET.get('q', '')
    if q:
        full_query = _fill_out_query(request, q)
        s = solr_connection()
        results = s.query(full_query.encode('utf8'), rows=50, 
            sort='date_created', sort_order='desc')
        paginator = solr.SolrPaginator(results)
        try:
            page = get_page(request, paginator)
            page.object_list = m.Entry.objects.filter(id__in=[r['id'] for r in page.object_list])
        except:
            page = None
        return render_to_response('index.html', {
            'q': q, 'title': 'Search for "%s"' % q,
            'page': page, 'query_param': 'q=%s&' % q,
            }, context)
    return render_to_response('index.html', context)


def search_feed (request):
    """
    FIXME: doesn't do opensearch right
    """
    context = RequestContext(request)
    q = request.GET.get('q', '')
    if q:
        s = solr_connection()
        r = s.query(q.encode('utf8'), rows=50, sort='date_created', sort_order='asc',
            **COMMON_FACET_PARAMS)
        paginator = SolrPaginator(q.encode('utf8'), r)
        try:
            page = get_page(request, paginator)
            return atom_feed(page=page, 
                title='latest for search "%s"' % q,
                link=reverse('search_feed'))
        except:
            page = None
    return render_to_response('index.html', context)
