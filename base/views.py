from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render_to_response
from django.template import RequestContext

from unalog2.base import models as m


def index (request):
    context = RequestContext(request)
    qs = m.Entry.objects.order_by('-date_created')
    qs = qs.exclude(is_private=True)
    paginator = Paginator(qs, 50)
    try:
        page_num = int(request.GET.get('page', '1'))
        if page_num not in paginator.page_range:
            raise ValueError, 'Invalid page number'
    except ValueError:
        page_num = 1
    page = paginator.page(page_num)
    return render_to_response('index.html', {'title': 'FOO', 
        'paginator': paginator, 'page': page, 
        }, context)