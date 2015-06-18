from django.shortcuts import render
from django.shortcuts import render, render_to_response, get_object_or_404
from django.template import RequestContext
from django.core.context_processors import csrf
from django.conf import settings
from django.contrib.auth import authenticate
import json
from django.http import HttpResponse
from decimal import Decimal
from django.db import models
from django.db.models import Q
import math, random
import time,datetime
import sys
import mongoengine
from props.models import *

#mongodb
#user = authenticate(username=settings._MONGODB_USER, password=settings._MONGODB_PASSWD)
#assert isinstance(user, mongoengine.django.auth.User)

# Create your views here.

def main(request={}):
    csrf_request = {}
    response = render_to_response('main.html',  csrf_request,context_instance=RequestContext(request))
    return response

def search(request):
    print 'in views.search'
    response = {}
    response['sales'] = []
    zipcode = int(request.GET.get( 'zip', 0 ))
    print 'zip = %s'%zipcode
    properties = Properties.objects.filter( zip = zipcode )  
    print 'about to iterate over filtered properties'
    for property in properties:
        for sale in property.sales:
            if ( sale.get('date','') != '' and sale.get('price', 0) != 0 ):
                response['sales'].append( { 'price' : sale['price'], 'date' : str(sale['date']) } )
    print 'done iterating  over filtered properties'
    response['sales'].sort( key=lambda sale : sale.get('date', '' ) )
    print 'about to converrt to json'
    json_str = json.dumps(response)
    print 'converrted to json'
    if ( sys.version_info > (2, 7) ):
        return HttpResponse(json_str, content_type='application/json')
    else:
      return HttpResponse(json_str, mimetype='application/json')
