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
print 'in props/views'

state_abbrevs = ['al','ak','az','ar','ca','co','ct','de','fl','ga','hi','id','il','in','ia','ks','ky','la','me','md','ma','mi','mn','ms','mo','mt','ne','nv','nh','nj','nm','ny','nc','nd','oh','ok','or','pa','ri','sc','sd','tn','tx','ut','vt','va','wa','wv','wi','wy']
states = ['alabama','alaska','arizona','arkansas','california','colorado','connecticut','delaware','florida','georgia','hawaii','idaho','illinois','indiana','iowa','kansas','kentucky','louisiana','maine','maryland','massachusetts','michigan','minnesota','mississippi','missouri','montana','nebraska','nevada','new hampshire','new jersey','new mexico','new york','north carolina','noth dakota','ohio','oklahoma','oregon','pennsylvania','rhode island','south carolina','south dakota','tennessee','texas','utah','vermont','virginia','washington','west virginia','wisconsin','wyoming']

class QueryTracker(object):

    def __init__( self, request ):
        print 'Initializing sales list'
        self.request = request
        self.response = {}
        self.query_dict = {}
        self.start_year = 1993

    def initSalesList( self ):
        print 'in initSalesList'
        self.response['sales'] = []

    def populateSalesList( self ):
        self.response['sales'] = []
        for i in range(len(self.sales_data)):
            self.response['sales'].append( { 'avg_price' : self.sales_data[i], 'period' : self.sales_dates[i] } )
        print 'about to calculate avg and roi'
        data_begun = False
        for period in range( len( self.response['sales'] ) ):
            if ( self.response['sales'][period]['avg_price'] != '' ):
                data_begun = True
                # roi calculation begins 1 after the first period with sales.
                # the first period with sales will always have roi = 1
                if ( period == 0 ): 
                    self.response['sales'][period]['roi'] = 1
                elif ( self.response['sales'][period-1]['avg_price'] == 0 ):
                    self.response['sales'][period]['roi'] = 1
                else:
                    self.response['sales'][period]['roi'] = 1.0*self.response['sales'][period-1]['roi'] * self.response['sales'][period]['avg_price'] / self.response['sales'][period-1]['avg_price']
                print 'period = %d roi = %s'%(period, str( self.response['sales'][period]['roi'] ))
            elif ( data_begun ):
                # if data has begun but we have a period that has no data, we have several options
                # we can do a linear interpolation, or we can simply assign it the last value, 
                # which will give some sharp edges but is simpler. will go withsimple approach for now
                self.response['sales'][period]['avg_price'] = self.response['sales'][period-1]['avg_price']
                self.response['sales'][period]['roi'] = self.response['sales'][period-1]['roi']
            else:
                self.response['sales'][period]['avg_price'] = 0
                self.response['sales'][period]['roi'] = 1
        print 'Exiting populateSalesList, data_begun = %d'%data_begun
                

    def isState( self, str ):
        if ( str in state_abbrevs or str in states ):
            return True
        return False

    def parseRequest( self ):
        print 'in parseRequest'
        self.search_term = self.request.GET.get( 'search_term', '' ) 
        self.query_metric = self.request.GET.get( 'query_metric', 'MedianSoldPrice_AllHomes' )
        print self.search_term
        #zip code?
        search_re = re.search( '^ *(\d+) *$', self.search_term )
        if ( search_re ):
            print 'searching for zip'
            self.collection = Zips
            self.query_dict['RegionName'] = str(search_re.group(1))
            self.response['header'] = self.query_dict['RegionName']
            self.response['type'] = 'zip'
            print 'zip = %s'%self.query_dict['RegionName']
            return
            
        # compound?  could be city, state or neighborhood, city
        search_re = re.search( '^ *(.*),\s+(.*) *$', self.search_term )
        if ( search_re ):
            if ( self.isState( str(search_re.group(1).lower() ) ) ):
                self.collection = Cities
                self.query_dict['RegionName'] = int(search_re.group(1))
                self.query_dict['State'] = int(search_re.group(2))
                self.response['header'] = self.query_dict['RegionName']
                print 'query for city %s'%self.query_dict['RegionName']
                self.response['type'] = 'city'
            else:
                self.collection = Neighborhoods
                self.query_dict['RegionName'] = int(search_re.group(1))
                self.query_dict['City'] = int(search_re.group(2))
                self.response['header'] = self.query_dict['RegionName']
                self.response['type'] = 'neighborhood'
                print 'query for neighborhood %s'%self.query_dict['RegionName']
            return
                
        # no comma? This will have to be improved, but for now, we look for if its a state,
        # then we see if we have a city in the db with this name, then county, then neighborhood
        # there are obvious caes where there could be both (la, new york counties), leaving as a FIXME
        search_re = re.search( '^ *(.*) *$', self.search_term )
        if ( search_re ):
            search_str = str(search_re.group(1).lower()) 
            if ( self.isState( search_str ) ):
                self.collection = States
                self.query_dict['RegionName'] = search_str
                self.response['header'] = self.query_dict['RegionName']
                self.response['type'] = 'state'
                print 'query for state %s'%self.query_dict['RegionName']
            elif( Cities.objects.filter( RegionName = search_str ).count() > 0 ):
                self.collection = Cities
                self.query_dict['RegionName'] = str(search_re.group(1))
                self.response['header'] = self.query_dict['RegionName']
                self.response['type'] = 'city'
                print 'query for city %s'%self.query_dict['RegionName']
            elif( Counties.objects.filter( RegionName = search_str ).count() > 0 ):
                self.collection = Counties
                self.query_dict['RegionName'] = str(search_re.group(1))
                self.response['header'] = self.query_dict['RegionName']
                self.response['type'] = 'county'
                print 'query for county %s'%self.query_dict['RegionName']
            elif( Neighborhoods.objects.filter( RegionName = search_str ).count() > 0 ):
                print 'query for neighborhood %s'%self.query_dict['RegionName']
                self.collection = Neighborhoods
                self.query_dict['RegionName'] = str(search_re.group(1))
                self.response['type'] = 'neighborhood'
                self.response['header'] = self.query_dict['RegionName']

    def filterProperties( self ):
        print 'in filterProperties'
        self.parseRequest()
    
        if ( self.query_dict != {} ):
            print self.query_metric
            self.sales_data =  self.collection.objects.filter( **self.query_dict ).only( self.query_metric )[0].to_mongo()[self.query_metric]
            print '%d sales'%(len( self.sales_data ))
            # The dates_dosument for each collection is stored as a document with RegionName 'dates_document'
            self.sales_dates = self.collection.objects.filter( RegionName = 'dates_document' ).only( '%s_dates'%self.query_metric )[0].to_mongo()['%s_dates'%self.query_metric]
            print '%d dates'%(len(self.sales_dates))
        else:
            print 'no filter!'
            self.sales_data = []

    def periodToIndex( self, year, month ):
        return 12*(year - self.start_year) + month - 1

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

    print 'done iterating  over filtered sales_data'
    json_str = json.dumps(qt.response)
    print 'converrted to json'
    if ( sys.version_info > (2, 7) ):
        return HttpResponse(json_str, content_type='application/json')
    else:
      return HttpResponse(json_str, mimetype='application/json')
