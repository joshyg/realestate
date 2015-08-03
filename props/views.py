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
        self.time_series_list = [ 'MedianSoldPrice_AllHomes', 'PriceToRentRatio_AllHomes', 'MedianSoldPricePerSqft_AllHomes',  'MedianSoldPricePerSqft_Condominum',
                                  'MedianSoldPricePerSqft_SingleFamilyResidence', 'MedianRentalPrice_AllHomes', 'MedianRentalPricePerSqft_AllHomes',
                                  'PctOfHomesIncreasingInValues_AllHomes', 'PctOfHomesDecreasingInValues_AllHomes', 'HomesSoldAsForeclosures_Ratio_AllHomes',
                                  'NumberOfHomesForRent_AllHomes', 'Turnover_AllHomes', 'SalePriceToListRatio_AllHomes', 
                                  'MedianListingPrice_AllHomes', 'MedianListingPricePerSqft_AllHomes', 'PctOfListingsWithPriceReductions_AllHomes'
                                ]
        self.collections = [ States, Cities, Counties, Neighborhoods, Zips ]
        self.types = [ 'state', 'city', 'county', 'neighborhood', 'zip' ]

    def initSalesList( self ):
        print 'in initSalesList'
        self.response['sales'] = []

    def populateSalesList( self ):
        self.response['sales'] = []
        for i in range(len(self.sales_data)):
            self.response['sales'].append( { 'avg_price' : self.sales_data[i], 'period' : self.sales_dates[i] } )
        print 'about to calculate avg and pct_change'
        data_begun = False
        for period in range( len( self.response['sales'] ) ):
            if ( self.response['sales'][period]['avg_price'] != '' ):
                data_begun = True
                # pct_change calculation begins 1 after the first period with sales.
                # the first period with sales will always have pct_change = 1
                # Initially I calculate pct_change as 'Multiple of initial period'
                # then I subtract 1 from each entry to get a % change
                if ( period == 0 ): 
                    self.response['sales'][period]['pct_change'] = 1
                elif ( self.response['sales'][period-1]['avg_price'] == 0 ):
                    self.response['sales'][period]['pct_change'] = 1
                else:
                    self.response['sales'][period]['pct_change'] = 1.0*self.response['sales'][period-1]['pct_change'] * self.response['sales'][period]['avg_price'] / self.response['sales'][period-1]['avg_price']
                print 'period = %d pct_change = %s'%(period, str( self.response['sales'][period]['pct_change'] ))
            elif ( data_begun ):
                # if data has begun but we have a period that has no data, we have several options
                # we can do a linear interpolation, or we can simply assign it the last value, 
                # which will give some sharp edges but is simpler. will go withsimple approach for now
                self.response['sales'][period]['avg_price'] = self.response['sales'][period-1]['avg_price']
                self.response['sales'][period]['pct_change'] = self.response['sales'][period-1]['pct_change']
            else:
                self.response['sales'][period]['avg_price'] = 0
                self.response['sales'][period]['pct_change'] = 1
        # convert multiple of initial value to pct change
        print ' converting multiple of initial value to % change'
        for period in range( len( self.response['sales'] ) ):
            self.response['sales'][period]['pct_change'] = 100*( self.response['sales'][period]['pct_change'] - 1 ) 
        print 'Exiting populateSalesList, data_begun = %d'%data_begun
                

    def isState( self, str ):
        if ( str in state_abbrevs or str in states ):
            return True
        return False

    def parseRequest( self ):
        print 'in parseRequest time_series = %d'%int( self.request.GET.get( 'data_type', 0 ) )
        self.search_term = self.request.GET.get( 'search_term', '' ) 
        self.time_series = self.time_series_list[ int( self.request.GET.get( 'data_type', 0 ) ) ]
        print self.search_term

        #specified in query?
        if ( self.request.GET.get( 'region_type', 'NA' ) != 'NA' ):
            self.collection = self.collections[int( self.request.GET.get( 'region_type', 'NA' ) )]
            self.query_dict['RegionName'] = self.search_term
            self.response['header'] = self.search_term
            self.response['type'] = self.types[int( self.request.GET.get( 'region_type', 'NA' ) )]
            print 'All query paramters gathered from advanced search'
            return

        #zip code?
        if ( self.checkForZipQuery( self.search_term ) ):
            return
            
        # compound?  could be city, state or neighborhood, city
        if ( self.checkForCompoundQuery( self.search_term ) ):
            return

        # no comma? This will have to be improved, but for now, we look for if its a state,
        # then we see if we have a city in the db with this name, then county, then neighborhood
        # there are obvious caes where there could be both (la, new york counties), leaving as a FIXME
        search_re = re.search( '^ *(.*) *$', self.search_term )
        if ( search_re ):
            search_str = str(search_re.group(1)).lower() 
            if ( self.checkForStateQuery(search_str) ):
                return
            if ( self.checkForCityQuery(search_str) ):
                return
            if ( self.checkForCountyQuery(search_str) ):
                return
            if ( self.checkForNeighborhoodQuery(search_str) ):
                return

    def checkForCompoundQuery( self, search_term ):
        print 'in checkForCompoundQuery'
        search_re = re.search( '^ *(.*),\s+(.*) *$', search_term )
        if ( search_re ):
            print 'Compound'
            search_str = str(search_re.group(1)).lower()
            state_str = str(search_re.group(2)).lower()
            if ( self.isState( state_str ) ):
                print 'City/County, State?'
                if ( state_str not in state_abbrevs ):
                    state_str = state_abbrevs[states.index(state_str)]
                if ( self.checkForCityQuery(search_str, state_str) ):
                    return True
                if ( self.checkForCountyQuery(search_str, state_str) ):
                    return True
                else:
                    print 'nope'
            city_str = str(search_re.group(2)).lower()
            for tmp_str in [ city_str, re.sub('(?i) *city', '', city_str) ]:
                if ( Cities.objects.filter( RegionName = tmp_str ).count() > 0 ):
                    print 'Neighborhood, City?'
                    if ( self.checkForNeighborhoodQuery(search_str) ):
                        self.query_dict['City'] = tmp_str
                        print 'query for neighborhood %s'%self.query_dict['RegionName']
                        return True
            return True
        return False
                
    def checkForZipQuery( self, search_term ):
        print 'in checkForZipQuery'
        search_re = re.search( '^ *(\d+) *$', search_term )
        if ( search_re ):
            print 'searching for zip'
            self.collection = Zips
            self.query_dict['RegionName'] = str(search_re.group(1))
            self.response['header'] = self.query_dict['RegionName']
            self.response['type'] = 'zip'
            print 'zip = %s'%self.query_dict['RegionName']
            return True
        return False

    def checkForStateQuery( self, search_str ):
        print 'in checkForStateQuery'
        search_str = re.sub('(?i) *state', '', search_str)
        if ( self.isState( search_str ) ):
            print '%s is a State'%search_str
            state_str = search_str
            if ( state_str not in state_abbrevs ):
                state_str = state_abbrevs[states.index(state_str)]
            self.collection = States
            self.query_dict['RegionName'] = search_str
            self.response['header'] = self.query_dict['RegionName']
            self.response['type'] = 'state'
            print 'query for state %s'%self.query_dict['RegionName']
            return True
        return False

    def checkForCityQuery( self, search_str, state_str = '' ):
        # Unlike with states and counties, city name convention is not 100% consistent
        # jersey city is saved as jersey city, but new york city is saved as new york
        print 'in checkForCityQuery'
        for tmp_str in [ search_str, re.sub('(?i) *city', '', search_str) ]:
            city_query_dict = { 'RegionName' : tmp_str }
            if ( state_str != '' ):
                city_query_dict['State'] = state_str
            city_query = Cities.objects.filter( **city_query_dict )
            if( city_query.count() > 0 ):
                print 'City %s found'%search_str
                self.collection = Cities
                self.query_dict['RegionName'] = tmp_str
                self.response['header'] = '%s, %s'%(self.query_dict['RegionName'], city_query[0].State)
                self.response['type'] = 'city'

                # If a state was passed in, add it to the query dict
                if ( state_str != '' ):
                    self.query_dict['State'] = state_str

                print 'query for city %s'%self.query_dict['RegionName']
                return True
        return False

    def checkForCountyQuery( self, search_str, state_str = '' ):
        print 'in checkForCountyQuery'
        search_str = re.sub('(?i) *county', '', search_str)
        county_query_dict = { 'RegionName' : search_str }
        if ( state_str != '' ):
            county_query_dict['State'] = state_str
        if( Counties.objects.filter( **county_query_dict ).count() > 0 ):
            print 'County %s found'%search_str
            self.collection = Counties
            self.query_dict['RegionName'] = search_str
            self.response['header'] = self.query_dict['RegionName']
            self.response['type'] = 'county'
            print 'query for county %s'%self.query_dict['RegionName']

    def checkForNeighborhoodQuery( self, search_str ):
        print 'in checkForNeighborhoodQuery'
        if( Neighborhoods.objects.filter( RegionName = search_str ).count() > 0 ):
            print 'Neighborhood %s found'%search_str
            self.collection = Neighborhoods
            self.query_dict['RegionName'] = search_str
            print 'query for neighborhood %s'%self.query_dict['RegionName']
            self.response['type'] = 'neighborhood'
            self.response['header'] = self.query_dict['RegionName']
            return True
        return False

    def filterProperties( self ):
        print 'in filterProperties'
        self.parseRequest()
    
        self.response['warning'] = ''
        if ( self.query_dict != {} ):
            print self.time_series
            self.sales_data =  self.collection.objects.filter( **self.query_dict )
            # if there is data, extract our time series
            if ( self.sales_data.count() > 0 ):
                self.sales_data = self.sales_data[0].to_mongo()[self.time_series]
            # its possible that the region has a data but not for the time series we are requesting.
            if ( len( self.sales_data ) > 0 ):
                print '%d sales'%(len( self.sales_data ))
                # The dates_dosument for each collection is stored as a document with RegionName 'dates_document'
                self.sales_dates = self.collection.objects.filter( RegionName = 'dates_document' ).only( '%s_dates'%self.time_series )
                print 'filter complete'
                self.sales_dates = self.sales_dates[0].to_mongo()['%s_dates'%self.time_series]
                print '%d dates'%(len(self.sales_dates))
                return True
            else:
                print 'No results for %s'%self.response['header']
                self.response['warning'] = 'No results for %s'%self.response['header']
                return False
        else:
            print 'no filter!'
            self.response['warning'] = 'No Region in db named %s'%self.search_term
            self.sales_data = []
            return False

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
    
    if ( qt.filterProperties() ):
        qt.populateSalesList()

    print 'done iterating  over filtered sales_data'
    json_str = json.dumps(qt.response)
    print 'converrted to json'
    if ( sys.version_info > (2, 7) ):
        return HttpResponse(json_str, content_type='application/json')
    else:
      return HttpResponse(json_str, mimetype='application/json')
