from django.core.paginator import Paginator
from django.http import Http404, HttpResponsePermanentRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from unalog2.base import models as m


def pagify(request, qs):
    paginator = Paginator(qs, 50)
    try:
        page_num = int(request.GET.get('p', '1'))
        if page_num not in paginator.page_range:
            raise ValueError, 'Invalid page number'
    except ValueError:
        page_num = 1
    page = paginator.page(page_num)
    return paginator, page

def index (request):
    context = RequestContext(request)
    qs = m.Entry.objects.order_by('-date_created')
    qs = qs.exclude(is_private=True)
    paginator, page = pagify(request, qs)
    return render_to_response('index.html', {
        'title': 'home', 
        'paginator': paginator, 'page': page, 
        }, context)
        

def person(request, user_name):
    return HttpResponsePermanentRedirect('/user/%s/' % user_name)

def user(request, user_name):
    context = RequestContext(request)
    user = get_object_or_404(m.User, username=user_name)
    qs = m.Entry.objects.filter(user=user)
    qs = qs.order_by('-date_created')
    qs = qs.exclude(is_private=True)
    paginator, page = pagify(request, qs)
    return render_to_response('index.html', {
        'title': 'user %s' % user_name,
        'paginator': paginator, 'page': page,
        'browse_type': 'user', 'browse_user': user, 
        'browse_user_name': user.username,
        }, context)
        
def user_tag(request, user_name, tag_name=''):
    context = RequestContext(request)
    user = get_object_or_404(m.User, username=user_name)
    qs = m.Entry.objects.filter(user=user, tags__name=tag_name)
    qs = qs.order_by('-date_created')
    qs = qs.exclude(is_private=True)
    paginator, page = pagify(request, qs)
    return render_to_response('index.html', {
        'title': "user %s's tag %s" % (user_name, tag_name),
        'paginator': paginator, 'page': page,
        'browse_type': 'tag', 'browse_user': user, 'tag': tag_name,
        }, context)
    
def user_tags(request, user_name):
    context = RequestContext(request)
    user = get_object_or_404(m.User, username=user_name)
    qs = m.Tag.objects.filter(entries__user=user)
    paginator, page = pagify(request, qs)
    return render_to_response('tags.html', {
        'title': "user %s's tags" % user_name,
        'paginator': paginator, 'page': page,
        'browse_user': user,
        }, context)


def url_all(request, md5sum=''):
    context = RequestContext(request)
    url = get_object_or_404(m.Url, md5sum=md5sum)
    qs = m.Entry.objects.filter(url=url)
    qs = qs.exclude(is_private=True)
    paginator, page = pagify(request, qs)
    return render_to_response('index.html', {
        'title': "url %s" % url.value[:50],
        'paginator': paginator, 'page': page,
        'browse_type': 'url', 'browse_url': url
        }, context)
    
