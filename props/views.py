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
import re
from props.models import *

#mongodb
#user = authenticate(username=settings._MONGODB_USER, password=settings._MONGODB_PASSWD)
#assert isinstance(user, mongoengine.django.auth.User)

# Create your views here.

#
#convert month/year into index in our response['sales'] array
#

state_abbrevs = ['al','ak','az','ar','ca','co','ct','de','fl','ga','hi','id','il','in','ia','ks','ky','la','me','md','ma','mi','mn','ms','mo','mt','ne','nv','nh','nj','nm','ny','nc','nd','oh','ok','or','pa','ri','sc','sd','tn','tx','ut','vt','va','wa','wv','wi','wy']
states = ['alabama','alaska','arizona','arkansas','california','colorado','connecticut','delaware','florida','georgia','hawaii','idaho','illinois','indiana','iowa','kansas','kentucky','louisiana','maine','maryland','massachusetts','michigan','minnesota','mississippi','missouri','montana','nebraska','nevada','new hampshire','new jersey','new mexico','new york','north carolina','noth dakota','ohio','oklahoma','oregon','pennsylvania','rhode island','south carolina','south dakota','tennessee','texas','utah','vermont','virginia','washington','west virginia','wisconsin','wyoming']

class QueryTracker(object):

    def __init__( self, request ):
        self.request = request
        self.response = {}
        self.query_dict = {}

    def initSalesList( self ):
        print 'in initSalesList'
        self.response['sales'] = []
        now = str(datetime.datetime.now()).split('-')
        current_yr=int(now[0])
        current_month=int(now[1])
        print 'current period = %d/%d'%(current_month, current_yr)
        for yr in range(1990,current_yr + 1):
            for month in range(1,13):
                if ( current_yr <= yr and current_month < month ):
                    break
                self.response['sales'].append({ 'period': '%d-%d'%(yr,month), 'count': 0, 'total_price': 0, 'avg_price': 0, 'roi' : 0 })
        print self.response['sales'][-1]

    def populateSalesList( self ):
        print 'about to iterate over properties'
        for property in self.properties:
            for sale in property.sales:
                print sale
                if ( sale.get('date','') != '' and sale.get('price', 0) != 0 ):
                    self.response['sales'][periodToIndex(sale['year'], sale['month'])]['total_price'] += sale['price']
                    self.response['sales'][periodToIndex(sale['year'], sale['month'])]['count'] += 1
        print 'about to calculate avg and roi'
        for period in range( len( self.response['sales'] ) ):
            if ( self.response['sales'][period]['count'] != 0 ):
                self.response['sales'][period]['avg_price'] = self.response['sales'][period]['total_price']/self.response['sales'][period]['count']
                # roi calculation begins 1 after the first period with sales.
                # the first period with sales will always have roi = 1
                if ( period == 0 or self.response['sales'][period-1]['roi'] == 0 or self.response['sales'][period-1]['avg_price'] == 0 ):
                    self.response['sales'][period]['roi'] = 1
                else:
                    self.response['sales'][period]['roi'] = 1.0*self.response['sales'][period-1]['roi'] * self.response['sales'][period]['avg_price'] / self.response['sales'][period-1]['avg_price']

    def isState( self, str ):
        if ( str in state_abbrevs or str in states ):
            return True
        return False

    def parseRequest( self, search_term ):
        print 'in parseRequest'
        #zip code?
        search_re = re.search( '^ *(\d+) *$', search_term )
        if ( search_re ):
            self.query_dict['zip'] = int(search_re.group(1))
            self.response['header'] = self.query_dict['zip']
            print 'zip = %s'%self.query_dict['zip']
            return
            
        # compound?  could be city, state or neighborhood, city
        search_re = re.search( '^ *(.*),\s+(.*) *$', search_term )
        if ( search_re ):
            if ( self.isState( str(search_re.group(1).lower() ) ) ):
                self.query_dict['city'] = int(search_re.group(1))
                self.query_dict['state'] = int(search_re.group(2))
                self.response['header'] = self.query_dict['city']
                print 'query for city %s'%self.query_dict['city']
            else:
                self.query_dict['neighborhood'] = int(search_re.group(1))
                self.query_dict['city'] = int(search_re.group(2))
                self.response['header'] = self.query_dict['neighborhood']
                print 'query for neighborhood %s'%self.query_dict['neighborhood']
            return
                
        # no comma? This will have to be improved, but for now, we look for if its a state,
        # then we see if we have a city in the db with this name, then county, then neighborhood
        # there are obvious caes where there could be both (la, new york counties), leaving as a FIXME
        search_re = re.search( '^ *(.*) *$', search_term )
        if ( search_re ):
            search_str = str(search_re.group(1).lower()) 
            if ( self.isState( search_str ) ):
                self.query_dict['state'] = seacrh_str
                self.response['header'] = self.query_dict['state']
                print 'query for state %s'%self.query_dict['state']
            elif( Properties.objects.filter( city = search_str ).count() > 0 ):
                self.query_dict['city'] = str(search_re.group(1))
                self.response['header'] = self.query_dict['city']
                print 'query for city %s'%self.query_dict['city']
            elif( Properties.objects.filter( county = search_str ).count() > 0 ):
                self.query_dict['county'] = str(search_re.group(1))
                self.response['header'] = self.query_dict['county']
                print 'query for county %s'%self.query_dict['county']
            elif( Properties.objects.filter( neighborhood = search_str ).count() > 0 ):
                print 'query for neighborhood %s'%self.query_dict['neighborhood']
                self.query_dict['neighborhood'] = str(search_re.group(1))
                self.response['header'] = self.query_dict['neighborhood']

    def filterProperties( self ):
        print 'in filterProperties'
        self.parseRequest( self.request.GET.get( 'search_term', '' ) )
    
        if ( self.query_dict != {} ):
            self.properties = Properties.objects.filter( **self.query_dict )
            print '%d results'%self.properties.count()
        else:
            print 'no filter!'
            self.properties = []

def periodToIndex( year, month ):
    return 12*(year - 1990) + month - 1

def main(request={}):
    csrf_request = {}
    response = render_to_response('main.html',  csrf_request,context_instance=RequestContext(request))
    return response

def search(request):
    print 'in views.search'

    qt = QueryTracker(request)

    qt.initSalesList()
    qt.filterProperties()
    qt.populateSalesList()

    print 'done iterating  over filtered properties'
    json_str = json.dumps(qt.response)
    print 'converrted to json'
    if ( sys.version_info > (2, 7) ):
        return HttpResponse(json_str, content_type='application/json')
    else:
      return HttpResponse(json_str, mimetype='application/json')
