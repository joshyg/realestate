from django.shortcuts import render
from django.shortcuts import render, render_to_response, get_object_or_404
from django.template import RequestContext
from django.core.context_processors import csrf
import json
from django.http import HttpResponse
from decimal import Decimal
from django.db import models
from django.db.models import Q
import math, random
from django.conf import settings
import time,datetime
import sys
import mongoengine
from props.models import *

#mongodb
user = authenticate(username=username, password=password)
assert isinstance(user, mongoengine.django.auth.User)

# Create your views here.

def main(request={}):
    csrf_request = {}
    response = render_to_response('main.html',  csrf_request,context_instance=RequestContext(request))
    return response

def search(request):
    print 'in views.search'
    response = {}
    response['sales'] = []
    zipcode = request.GET.get( 'zip', 0 )
    properties = Properties.objects.filter( zip = sip )  
    for property in properties:
        response['sales'].append( property.sales )
    response['sales'].sort( key=lambda sale : sale.date )
    print 'about to converrt to json'
    json_str = json.dumps(response)
  if ( sys.version_info > (2, 7) ):
      return HttpResponse(json_str, content_type='application/json')
  else:
      return HttpResponse(json_str, mimetype='application/json')
