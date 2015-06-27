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

#
#convert month/year into index in our response['sales'] array
#
def periodToIndex( year, month ):
    return 12*(year - 1990) + month

def main(request={}):
    csrf_request = {}
    response = render_to_response('main.html',  csrf_request,context_instance=RequestContext(request))
    return response

def search(request):
    print 'in views.search'
    response = {}
    response['sales'] = []

    for yr in range(1990,2016):
        for month in range(1,13):
            response['sales'].append({ 'period': '%d-%d'%(yr,month), 'count': 0, 'total_price': 0, 'avg_price': 0 })

    zipcode = int(request.GET.get( 'zip', 0 ))
    # send back the zipcode from the request
    response['zip'] = zipcode
    print 'zip = %s'%zipcode

    properties = Properties.objects.filter( zip = zipcode )  
    print 'about to iterate over properties'
    for property in properties:
        for sale in property.sales:
            if ( sale.get('date','') != '' and sale.get('price', 0) != 0 ):
                response['sales'][periodToIndex(sale['year'], sale['month'])]['total_price'] += sale['price']
                response['sales'][periodToIndex(sale['year'], sale['month'])]['count'] += 1
    for period in range( len( response['sales'] ) ):
        if ( response['sales'][period]['count'] != 0 ):
            response['sales'][period]['avg_price'] = response['sales'][period]['total_price']/response['sales'][period]['count']

    print 'done iterating  over filtered properties'
    json_str = json.dumps(response)
    print 'converrted to json'
    if ( sys.version_info > (2, 7) ):
        return HttpResponse(json_str, content_type='application/json')
    else:
      return HttpResponse(json_str, mimetype='application/json')
