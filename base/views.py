from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.http import HttpResponsePermanentRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils import feedgenerator

from unalog2.base import models as m


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


def pagify(request, qs):
    """
    Convenience helper to paginate out a query set.
    """
    paginator = Paginator(qs, 50)
    try:
        page_num = int(request.GET.get('p', '1'))
        if page_num not in paginator.page_range:
            raise ValueError, 'Invalid page number'
    except ValueError:
        page_num = 1
    page = paginator.page(page_num)
    return paginator, page


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


def login_view(request):
    """
    Log a user into the system.
    """
    context = RequestContext(request)
    next_path = request.POST.get('next', '/')
    # First check to see if they're already logged in
    if request.user.is_authenticated():
        return HttpResponseRedirect(next_path)
        
    if request.method == 'POST':
        try: 
            username = request.POST.get('user_id', None)
            password = request.POST.get('user_pass', None)
            user = authenticate(username=username, password=password)
            if user is None:
                raise Exception('Could not authenticate: user is None')
            if user.is_active:
                login(request, user)
                request.user.message_set.create(message='Logged in.')
                return HttpResponseRedirect(next_path)
            else:
                raise Exception('User not active')
        except Exception, e:
            # FIXME: log appropriately, please
            #import traceback
            #print traceback.print_exc()
            pass
    # Assume it didn't work, or their cookies are disabled, or they GET'd.
    request.session['message'] = 'Invalid username or password.  Please try again.'
    return HttpResponseRedirect(next_path)

    
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