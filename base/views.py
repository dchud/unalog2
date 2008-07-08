from django.http import Http404
from django.shortcuts import render_to_response


from unalog2.base import models as m



def index (request):
    return render_to_response("index.html", {'title': "FOO"})