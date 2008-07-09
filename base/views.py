from django.http import Http404
from django.shortcuts import render_to_response
from django.template import RequestContext

from unalog2.base import models as m


def index (request):
    qs = m.Entry.objects.order_by('-date_created')
    qs = qs.exclude(is_private=True)
    return render_to_response("index.html", {'entries': qs[:50],
        'title': "FOO"}, RequestContext(request))