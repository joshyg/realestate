#!/usr/local/bin/python2.7
import urllib2 as url
import datetime
import pymongo
import pprint, json, re, time, random, threading
import argparse
pp = pprint.PrettyPrinter(indent=4)

months = [ '', 'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec' ]
states = ['al','ak','az','ar','ca','co','ct','de','fl','ga','hi','id','il','in','ia','ks','ky','la','me','md','ma','mi','mn','ms','mo','mt','ne','nv','nh','nj','nm','ny','nc','nd','oh','ok','or','pa','ri','sc','sd','tn','tx','ut','vt','va','wa','wv','wi','wy']

class TruliaParser( object):
    def __init__( self, host='localhost', username='', password='', port=27017 ):
        self.client = pymongo.MongoClient(host=host, port=port)
        self.db = self.client['real_estate'] # will be created if it doesn't already exist
        self.db.authenticate(username, password)
        self.collection = self.db['properties']
        self.populated_regions_collection = self.db['populated_regions']
        self.print_output=False
        self.update_properties_db=True
        self.update_populated_regions_db=False
        self.debug = False
        self.write_size = 10
        self.property_update_array = []
        self.properties = []
        # vars used for multithreading/interthread communication
        self.threads=1
        self.lock = threading.RLock()
        self.x = 0
        self.y = 0
        self.count=0

        #region parsing parameters, default is SF
        self.width=.001
        self.height=.003
        self.zoom=19
        # rectangular boundary of our search
        self.x_start=37.681
        self.x_end=37.810
        self.y_start=-122.51
        self.y_end=-122.350 
        # increment may be smaller than width/height, cautious step to make sure we dont lose boundary properties
        self.x_increment=.0008
        self.y_increment=.0024
        # init vars are used for when we have to stop and restart script in the middle of a scrape
        self.x_init = self.x_start
        self.y_init = self.y_start
    

    def find_trulia_id( self, property, line ):
        if ( line.find('data-property-id=') >= 0 ):
            property['trulia_id'] = int(re.search('data-property-id="(\d+)"', line).group(1))
            return True
        return False
    
    def find_state( self, property, line ):
        if( line.find('data-property-state-code=')  >= 0 ):
            property['state'] = states.index( str(re.search('data-property-state-code="(\S+)"', line).group(1)).lower() )
            return True
        return False

    def find_latitude( self, property, line ):
        if( line.find('<meta itemprop="latitude" content=') >= 0):
            property['latitude'] = str(re.search('<meta itemprop="latitude" content="(.*)">', line).group(1))
            return True
        return False

    def find_longitude( self, property, line ):
        if( line.find('<meta itemprop="longitude" content=') >= 0):
            property['longitude'] = str(re.search('<meta itemprop="longitude" content="(.*)">', line).group(1))
            return True
        return False

    def find_trulia_link( self, property, line ):
        if( line.find('itemprop="url" data-row-index=') >= 0 ):
            property['trulia_link'] = str(re.search('<a.*itemprop="url"\s+data-row-index="\d+"\s+href="(\S+)"', line).group(1))
            return True
        return False

    # I originally put this in, but it seems to always be the same as adress
    def find_name( self, property, line ):
        if( line.find('<meta itemprop="name" content="') >= 0 ):
            property['name'] = str(re.search('<meta itemprop="name" content="(.*)">', line).group(1)).lower()
            return True
        return False

    def find_address( self, property, line ):
        if( line.find('<meta itemprop="streetAddress" content="') >= 0 ):
            property['address'] = str(re.search('<meta itemprop="streetAddress" content="(.*)">', line).group(1)).lower()
            return True
        return False

    def find_neighborhood( self, property, line ):
        line_re = re.search( '<strong>Neighborhood</strong> *(.*)</li>', line )
        if ( line_re ):
            property['neighborhood'] = str(line_re.group(1)).lower()
            return True
        return False
    def find_last_price( self, property, line ):
        if( line.find('span class="h4"') >= 0 ):
            self.in_price_span = True
            return True
        elif( self.in_price_span ):
            line_re = re.search('<b>\$([\d,]+)</b>', line)
            if( line_re ):
                property['sales'][-1]['price'] = int(str(line_re.group(1)).replace(',', ''))
                self.in_price_span = False
                return True
        return False
    def find_last_sold_date( self, property, line ):
        if( line.find('Last sold on') >= 0 ):
            line_re = re.search('Last sold on\s+(\S+)\s+(\d+),\s+(\d{4})</div>', line)
            if( line_re ):
                month = months.index(str(line_re.group(1)).lower())
                day  = int(line_re.group(2))
                year  = int(line_re.group(3))
                property['sales'][-1]['day']   = day
                property['sales'][-1]['month'] = month
                property['sales'][-1]['year']  = year
                property['sales'][-1]['date'] =  datetime.datetime(year,month,day, 0, 0)
                return True
        return False
    def find_num_beds( self, property, line ):
        if( line.find('beds</strong>')):
            line_re = re.search('(\d+)\s+beds', line)
            if( line_re ):
                property['num_beds'] = int(line_re.group(1))
                return True
        return False
    def find_city_and_zip( self, property, line ):
        line_re = re.search('"addressLocality">([^<]+)</span>,.*<span itemprop="postalCode">(\d+)</span>', line)
        if( line_re ):
            property['city'] = str(line_re.group(1))
            property['zip'] = int(line_re.group(2))
            return True
        return False
    def find_type( self, property, line ):
        line_re = re.search('<strong>(Condo|Single-Family Home|Multi-Family)', line)
        if( line_re ):
            property['type'] = str(line_re.group(1)).lower()
            return True
        return False
    def find_sqft( self, property, line ):
        line_re = re.search('([\d,]+)\s+sqft', line)
        if( line_re ):
            property['sqft'] = int(str(line_re.group(1)).replace(',', ''))
            return True
        return False


    def format_line( self, line ): 
        line = str( re.sub(' *data:| *assessor_data:', '', line) )
        line = str( re.sub('\n', '', line) )
        line = str( re.sub(' *$', '', line) )
        line = str( re.sub('^ *', '', line) )
        line = str( re.sub(',$', '', line) )
        return line

    def collect_past_sales( self, start_address='', end_address='' ):
        if ( self.debug ):
            print start_address
        requests = []
        start = False

        for property in  self.collection.find({'parsed_past_sales' : 0 }):
            property_found = False

            if ( property['parsed_past_sales'] == 1 ):
                continue

            # I have seen unexplainable transient db access errors
            # adding retry mechanism until issue is root caused.
            for i in range( 5 ):
                try:
                    # multiple instances of this script may be running on multiple machines.
                    # In order to avoid reparsing the same property, I need to atomically check
                    # whether parsing has begun and, if not, declare that it has begun before parsing.
                    # At some point I should also write a method to look for properties that began
                    # but never finished, possibly due to a lost connection or some other bug.
                    property = self.collection.find_one_and_update( { '_id' : property['_id'], 'parsing_past_sales' : 0 }, { '$set' : { 'parsing_past_sales' : 1 } } )
                    if ( property ):
                        property_found = True
                    break
                except:
                    print 'db access error on property #%d'%count

            if ( not property_found ):
                continue
            if ( start_address != ''):
                if ( property['address'] == start_address ):
                    start = True
                if ( not start ):
                    continue
            if ( end_address != '' ):
                if ( property['address'] == end_address ):
                    break
            if ( property['parsed_past_sales'] == 1 ):
                continue
            
            if ( self.debug ):
                print 'parsing %s'%property['trulia_link']
            req = url.Request('http://www.trulia.com%s' % property['trulia_link'])
            req.add_header('User-agent', 'Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11')
            url_found=False
            for retry in range(5):
                try:
                    r = url.urlopen(req)
                    url_found=True
                    break
                except:
                    if ( self.debug ):
                        print ('retry #%d on %s'%( retry, property['trulia_link'] ) )
                        time.sleep(4+random.randint(0,3))

            if ( not url_found ):
                self.properties.update( { '_id' : properties[count]['_id'], 'parsing_past_sales' : 0 }, { '$set' : { 'parsing_past_sales' : 0 } } )
                continue

                
            price = -1
            date = ''
            updates_made = False
            date_line = False
            sale_line = False
            sales_section_begun = False
            for line in r.readlines():
                """
                      <div class="col cols7 pls">Recording Date</div>
                      <div class="col lastCol pln">10/28/2014</div>
                    </li>
                                  <li class="line">
                      <div class="col cols7 pls">Contract Date</div>
                      <div class="col lastCol pln">10/27/2014</div>
                    </li>
                                  <li class="line">
                      <div class="col cols7 pls">Sale Price</div>
                      <div class="col lastCol pln">$830,000</div>
                """
                if( line.find( 'Recording Date' ) >= 0 ):
                    sales_section_begun = True
                    date_line = True
                    continue
                if( line.find( 'Sale Price' ) >= 0 ):
                    sales_section_begun = True
                    sale_line = True
                    continue
                if( date_line ):
                    line_re = re.search('(\d{2})/(\d{2})/(\d{4})</div>', line)
                    if ( line_re ):
                        month = int(line_re.group(1))
                        day = int(line_re.group(2))
                        year = int(line_re.group(3))
                        date = datetime.datetime(year,month,day,0,0)
                    date_line = False
                    continue
                if( sale_line ):
                    line_re = re.search( '\$([\d,]+)</div>', line )
                    if ( line_re ):
                        price = int( str( line_re.group(1) ).replace( ',', '' ) )
                    sale_line = False
                if ( price != -1 and date != '' ):
                    sale_record = { 'day' : day, 'month' : month, 'year' : year, 'date' : date, 'price' : price }
                    if ( sale_record not in property['sales'] ):
                        property['sales'].append( sale_record )
                        updates_made = True
                    price = -1
                    date = ''
                if ( ( line.find('Real Estate Trends') >= 0 or line.find('Estimates') >= 0 ) and sales_section_begun ):
                    break

            if( updates_made ):
                if ( self.debug ):
                    print 'updating %s'%property['address']
                requests.append( pymongo.UpdateOne( { '_id' : property['_id'] }, { '$set' : { 'sales' : property['sales'], 'parsed_past_sales' : 1 } } ) )
            else:
                requests.append( pymongo.UpdateOne( { '_id' : property['_id'] }, { '$set' : { 'parsed_past_sales' : 1 } } ) )

            if ( len( requests ) >= self.write_size ):
                if ( self.debug ):
                    print 'BULK WRITE!'
                self.collection.bulk_write( requests )
                requests = []

        if ( requests != [] ):
            print 'BULK WRITE!'
            self.collection.bulk_write( requests )
        
                      
                
        

    def save_properties( self ):
        requests = []
        self.lock.acquire()
        for property in self.properties:
            if( not self.collection.find_one( { 'address' : property['address'], 'zip' : property['zip'] } ) ):
                requests.append( pymongo.InsertOne( property ) )
                if( self.debug ):
                    print 'inserting '+property['address']
            elif ( self.debug ):
                print property['address']+' is in db'
        self.lock.release()
        if ( requests != [] ):
            if ( self.debug ):
                print 'writing!'
            self.collection.bulk_write( requests )

    def update_properties( self ):
        if ( self.debug ): 
            print 'in update_properties, property_update_array = ',
            print self.property_update_array
        requests = []
        self.lock.acquire()
        if ( self.property_update_array != [] ):
            for property in self.properties:
                for field in self.property_update_array:
                    if ( field != 'sales' ):
                        requests.append( pymongo.UpdateOne( { 'address' : property['address'], 'zip' : property['zip'] }, { '$set' : { field : property[field] } } ) )
                    else:
                        # because it is an embedded list, sales property must be dealt with differently.
                        requests.append( pymongo.UpdateOne( { 'address' : property['address'], 'zip' : property['zip'] }, { '$push' : { field : property[field] } } ) )
                    
        self.lock.release()
        if ( requests != [] ):
            self.collection.bulk_write( requests )
        



    def parse_zipsearch_url( self, my_url ):
        self.properties = []
        self.in_price_span = False
        req = url.Request(my_url)
        req.add_header('User-agent', 'Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11')
        r = url.urlopen(req)
        property = None
        for line in r.readlines():
            if ( line.find( 'data-list-index=' ) >= 0 ):
                if ( property != None ):
                    self.lock.acquire()
                    self.properties.append( property )
                    self.lock.release()
                property = { 'address' : '', 'city' : '', 'state' : '',  'zip': 0, 'neighborhood' : '',
                             'sqft' : 0, 'num_beds' : 0, 'num_baths' : 0, 'num_park' : 0,
                             'trulia_id' : 0, 'trulia_link' : '', 'latitude' : 0, 'longitude' : 0, 'type' : '',
                             'sales' : [  { 'day' : 0, 'month' : 0, 'year': 0, 'date' : 0, 'price' : 0 } ],
                             'parsed_past_sales' : 0, 'parsing_past_sale' : 0  }
            if ( self.find_trulia_id( property, line ) ):
                continue
            if ( self.find_state( property, line ) ):
                continue
            if ( self.find_latitude( property, line ) ):
                continue
            if ( self.find_longitude( property, line ) ):
                continue
            if ( self.find_trulia_link( property, line ) ):
                continue
            if ( self.find_address( property, line ) ):
                continue
            if ( self.find_last_price( property, line ) ):
                continue
            if ( self.find_last_sold_date( property, line ) ):
                continue
            if ( self.find_num_beds( property, line ) ):
                continue
            if ( self.find_city_and_zip( property, line ) ):
                continue
            if ( self.find_neighborhood( property, line ) ):
                continue
            if ( self.find_type( property, line ) ):
                continue
            if ( self.find_sqft( property, line ) ):
                continue

        self.save_properties()
        self.update_properties()

    def parse_json( self, json_list ):
        for entry in json_list:
            property = { 'address' : '', 'city' : '', 'state' : '',  'zip': 0, 'neighborhood' : '',
                                'sqft' : 0, 'num_beds' : 0, 'num_baths' : 0, 'num_park' : 0,
                                'trulia_id' : 0, 'trulia_link' : '', 'latitude' : 0, 'longitude' : 0, 'type' : '',
                                'sales' : [  { 'day' : 0, 'month' : 0, 'year': 0, 'date' : 0, 'price' : 0 } ],
                                'parsed_past_sales' : 0, 'parsing_past_sale' : 0  }

            bed_bath_re = re.search('(\d+)bd,\s+(\d+)\s+\S+\s+ba', entry['formattedBedAndBath']) # 2bd, 2 full ba 
            if ( bed_bath_re ):
                property['num_beds'] =  int( bed_bath_re.group(1) )
                property['num_baths'] = int( bed_bath_re.group(2) )
    
            property['sales'] = [ {'day' : 0, 'month': 0, 'year': 0, 'date' : 0, 'price' : 0 } ] 
            date_re = re.search('(\S+)\s+(\d+),\s+(\d{4})', str( entry['lastSaleDate'] ) )                            #'Jun 30, 2005',
            if ( date_re ):
                month = months.index( str( date_re.group(1) ).lower() )
                day  = int(date_re.group(2))
                year  = int(date_re.group(3))
                property['sales'][0]['day']  =   day
                property['sales'][0]['month'] =  month
                property['sales'][0]['year']  =  year
                property['sales'][0]['date'] = datetime.datetime(year,month,day,0,0)
            property['sales'][0]['price'] = int( entry['lastSalePrice'].replace('$','').replace(',','') )    #$769,000'

            if( entry['formattedSqft'] != '' ):
                property['sqft'] = int(entry['formattedSqft'].replace(',', '').replace(' sqft', ''))         #'1,128 sqft',
            else:
                property['sqft'] = 0

            property['city'] = entry['city'].lower()#'San Francisco'
            property['county'] = entry['county'].lower()# 'San Francisco',
            property['latitude'] = entry['latitude']                                                         #37.751404
            property['longitude'] = entry['longitude']                                                       #-122.40685
            property['trulia_link'] = entry['pdpURL']                                                        #'/homes/California/San_Francisco/sold/26697877-2964-25th-St-302-San-Francisco-CA-94110',
            property['address'] = entry['shortDescription'].lower()                                          #'2964 25th St #302',
            property['state'] = states.index( entry['stateCode'].lower() )                                   #'CA',
            property['type'] = entry['typeDisplay'].lower()                                                  #'Condo',
            property['zip'] = int( entry['zipCode'] )                                                        #'94110'
            if ( entry.get('neighborhood', None) != None ):
                property['neighborhood'] = entry['neighborhood'].lower()                                     #Mission
            else:
                property['neighborhood'] = ''

            self.lock.acquire()
            if ( self.debug ):
                print 'appending %s to property list'%property['address']
            self.properties.append( property )
            if ( len( self.properties ) >= self.write_size ):
                self.save_properties()
                self.update_properties()
                self.properties = []
            self.lock.release()

        self.lock.acquire()
        if ( self.properties != [] ):
            self.save_properties()
            self.update_properties()
            self.properties = []
        self.lock.release()

    # the following methon assumes a file in which each line is a json object,
    # but no object spans multiple lines.  It is based on current use cases, there may be
    # a time when we have an entire file that is one json object, this is not for that
    def parse_json_file ( self, input_file ):
        json_data = open( input_file )
        for line in json_data.readlines():
            try:
                self.parse_json( json.loads( line ) )
            except:
                print 'not valid json: %s'%line

    def parse_region( self, thread ):

            self.lock.acquire()
            if ( self.x == 0 and self.y == 0 ):
                self.x,self.y = self.x_init, self.y_init
            self.lock.release()

            while ( True ):

                # beginning of critical section
                self.lock.acquire()
                x, y = round(self.x,3), round(self.y,3)
                self.y += self.y_increment
                if ( self.y > self.y_end ):
                    self.y =  self.y_start 
                    self.x += self.x_increment
                self.lock.release()
                # end of critical section

                if ( x > self.x_end ):
                    break

                self.parse_map_url(x, y)

    def parse_map_url( self, x, y ):
        x_end = round(x+self.width, 3)
        y_end = round(y+self.height, 3)
        if ( self.debug ):
            print '%s parsing http://www.trulia.com/sold/%d_zm/%f,%f,%f,%f_xy/map_v/'%(threading.currentThread().getName(), self.zoom, x, x_end, y, y_end)
        my_url = 'http://www.trulia.com/sold/%d_zm/%f,%f,%f,%f_xy/map_v/'%(self.zoom, x, x_end, y, y_end)
        req = url.Request(my_url)
        req.add_header('User-agent', 'Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11')
        for retry in range(5):
            try:
                r = url.urlopen(req)
                for line in r.readlines():
                    # data is the recently sold homes in the location assessor_data is all other homes in the location
                    if ( line.find('data:') >= 0 ):
                        line = self.format_line( line )
                        if ( line != ''  and line != '[]' ):
                            if ( self.print_output ):
                                print line
                            if( self.update_populated_regions_db ):
                                region = { 'x_start' : x, 'x_end' : x_end, 'y_start' : y, 'y_end': y_end, 'fully_parsed' : 0}
                                self.populated_regions_collection.insert_one( region )
                                # if we are not updating the properties db, we can stop once we know the region has properties/population
                                if ( not self.update_properties_db ):
                                    break
                            if( self.update_properties_db ):
                                self.parse_json( json.loads( line ) ) 
                break
            except:
                print 'failure at %s'%my_url
                time.sleep(4+random.randint(0,3))

    def parse_map_file( self, my_file ):
        r = open( my_file, 'r ')
        for line in r.readlines():
            # data is the recently sold homes in the location assessor_data is all other homes in the location
            if ( line.find('data:') >= 0 ):
                line = self.format_line( line )
                if ( line != ''  and line != '[]' ):
                    if ( self.print_output ):
                        print 'line: %s.'%line
                    if( self.update_properties_db ):
                        self.parse_json( json.loads( line ) ) 


    def update_sales_format( self ):
        requests = []
        for document in self.collection.find():
            tmp_sales = []
            for sale in document['sales']:
                try:
                    tmp_sales.append( { 'price' : sale['price'],
                                        'year'  : sale['year'],
                                        'month' : sale['month'],
                                        'day'   : sale['date'],
                                        'date'  : datetime.datetime(sale['year'],sale['month'],sale['date'],0,0)
                                      } )
                except:
                    pass
            if ( tmp_sales != [] ):
                if ( self.debug ):
                    print tmp_sales
                else:
                    requests.append( pymongo.UpdateOne( { '_id' : document['_id'] }, { '$set' : { 'sales' : tmp_sales } } ) )
                if ( len( requests ) >= self.write_size ):
                    self.collection.bulk_write( requests )
                    requests = []

        if ( len( requests ) > 0 ):
            self.collection.bulk_write( requests )
            requests = []
                   
    def write_field(self, field, val):
        if ( self.debug ):
            print 'updating %s to %s'%(field,val)
        if ( re.search('^[0-9]*$', val) ):
            val = int( val )
        requests = []
        for document in self.collection.find():
            requests.append( pymongo.UpdateOne( { '_id' : document['_id'] }, { '$set' : { field : val } } ) )
        self.collection.bulk_write( requests )

    def backup(self):
        self.backup_collection = self.db['backup']
        self.backup_collection.remove()
        requests = []
        for document in self.collection.find():
            requests.append( pymongo.InsertOne( document ) )
        self.backup_collection.bulk_write( requests )

    def find_zips( self ):
        zip_list = []
        for prop in self.properties.find( {}, {'zip' : 1 } ):
            if prop['zip'] not in zip_list:
                zip_list.append( prop['zip'] )
        return zip_list

    # run once a day to get most recent updates for each zip.
    # a little add hoc because we don't know how many pages per zip
    # but since they are ordered by date, we really only need to f=do a few
    def daily_update( self ):
        for zipcode in self.find_zips():
            for page in range( 10 ):
                my_url = 'http://www.trulia.com/sold/zipcode_zip/%d_p'%(zipcode, page)
                self.property_update_array.append('sales')
                self.parse_zipsearch_url( my_url )

    def config_find_populated_regions( self ):
        # we are not updating our main collection, only the helper db populated_regions
        self.update_properties_db = False
        self.update_populated_regions_db = True
        # rule of thumb: make the boundaries multiples of .05.  This will make ot easier to check if a region is populated later 
        self.x_start = 24.55
        self.y_start = -125.0
        self.x_end = 49.0
        self.y_end = -67.20
        self.width = .1
        self.height = .1
        self.x_increment = .1
        self.y_increment = .1
        self.zoom = 13
    
    def config_parse_region( self ):
        self.zoom        = 19
        self.width       = .001
        self.height      = .003
        self.x_increment = .0009
        self.y_increment = .0027

    def config_hipri_region( self ):
        region = self.populated_regions_collection.find_one_and_update ( { 'priority' : 1, 'fully_parsed' : 0, 'processing_begun' : 0 }, { '$set' : { 'processing_begun' : 1 } } )
        self.x_start = region['x_start']
        self.x_end   = region['x_end']
        self.y_start = region['y_start']
        self.y_end   = region['y_end']
        self.x_init  = region['x_start']
        self.y_init  = region['y_start']
        self.zoom=19
        self.width = .001
        self.height = .003
        self.x_increment = .0008
        self.y_increment = .0024

    def parse_coordinates( self, input_coordinates ):
        # If 4 coordinates are given we interpret it as the boundaries of our rectangle.
        # if 6 are given we interpret the first four as the boundaries for our rectangle, and the last two the start point (maybe we had to stop the script and restart)
        # If 2 are given  we interpret it as the initialization point for the default rectangle
        coordinates = []
        coordinates = [ float(i) for i in input_coordinates ]
        if ( len( coordinates ) >= 4 ):
            self.x_start, self.x_end = coordinates[0], coordinates[1]
            self.y_start, self.y_end = coordinates[2], coordinates[3]
            self.x_init, self.y_init = self.x_start, self.y_start
            if ( len( coordinates ) >= 6 ): 
                self.x_init, self.y_init = coordinates[4], coordinates[5]
        elif ( len(coordinates) == 2 ):
            self.x_init, self.y_init = coordinates[0], coordinates[1]
            
    def worker( self, args={}, thread=0 ):
        if ( args.parse_json_file != '' ):
            self.parse_json_file(args.parse_json_file)
    
        if ( args.parse_map_file  != '' ):
            self.parse_map_file(args.parse_map_file)
    
        if ( args.parse_zipsearch_url != '' ):
            #self.parse_zipsearch_url('http://www.trulia.com/sold/94114_zip/%d_p'%i)
            self.parse_zipsearch_url(args.parse_zipsearch_url)
    
        if ( args.collect_past_sales):
            self.collect_past_sales(start_address=args.start_address, end_address=args.end_address)
    
        if ( args.update_sales_format ):
            self.update_sales_format()
    
        if ( args.write_field != '' and args.write_val != '' ):
            self.write_field( args.write_field, args.write_val )

        if ( args.parse_region or args.parse_hipri_region or args.find_populated_regions ):
            
            if ( args.parse_region ):
                self.config_parse_region()

            elif( args.parse_hipri_region ):
                self.config_hipri_region()
                
            elif ( args.find_populated_regions ):
                self.config_find_populated_regions()

            #cmdline args overwrite default
            coordinates = self.parse_coordinates( args.coordinates )

            self.parse_region( thread )

            if ( args.parse_region or args.parse_hipri_region ):
                if( self.populated_regions_collection.find_one( { 'x_start' : self.x_start, 'y_start' : self.y_start,'x_end' : self.x_end, 'y_end' : self.y_end } ) ):
                    self.populated_regions_collection.update_one( { 'x_start' : self.x_start, 'y_start' : self.y_start,'x_end' : self.x_end, 'y_end' : self.y_end }, { '$set' : { 'fully_parsed' : 1 } } )
                    if ( self.debug ):
                        print 'marked region as fully parsed.'

        if ( args.backup ):
            self.backup()

        if ( self.debug ):
            print '%s complete'%threading.currentThread().getName()
        return

if ( __name__ == '__main__' ):

    parser = argparse.ArgumentParser()
    parser.add_argument('--username',            type=str, default='joshyg',        help='username for db access')
    parser.add_argument('--password',            type=str, default='',              help='password for db access')
    parser.add_argument('--host',                type=str, default='localhost',     help='host for db access, default is localhost')
    parser.add_argument('--port',                type=str, default=11495,           help='port for db access, default is 11495')
    parser.add_argument('--debug',               action='store_true')
    parser.add_argument('--print_output',        action='store_true',               help='''print the output generated from file or url parsing.
                                                                                            Useful when we want to creat data files, as opposed to populating the db''')
    parser.add_argument('--parse_json_file',     type=str, default='',              help='parse a json file passed in from cmdline.   File is interpretted as one json object per line')
    parser.add_argument('--parse_map_file',      type=str, default='',              help='parse a file base on the output of a trulia map url')
    parser.add_argument('--parse_region',        action='store_true',               help='''parse a region delimited by 4 input paramaters: x_start, y_start, x_end, y_end,
                                                                                            where start point SW and end point is NE''')
    parser.add_argument('--parse_hipri_region',  action='store_true',               help='''parse a region that has priority = 1.  Selection is random''' )
    
    parser.add_argument('--find_populated_regions',        action='store_true',     help='''parse a region delimited by 4 input paramaters: x_start, y_start, x_end, y_end,
                                                                                            where start point SW and end point is NE.  Determine if subregion within the region has any population at all
                                                                                            If it does we add it to the populated regions collection.  Later we will iterate over each region in this collection
                                                                                            at a much finer granularity.''')
    parser.add_argument('coordinates',           nargs='*')
    parser.add_argument('--parse_zipsearch_url', type=str, default='',              help='parse a url provided on cmdline containing recetn sales in a given zip')
    parser.add_argument('--collect_past_sales',  action='store_true',               help='go through each property in our db whose past sales haven\'t been collected.  collect them')
    parser.add_argument('--daily_update',        action='store_true',               help='go through each zipcode in our db and see if there has been any activity lately')
    parser.add_argument('--start_address',       type=str, default='',              help='used with collect_past_sales, tells script to only begin inspection after a certain address in the db' )
    parser.add_argument('--end_address',         type=str, default='',              help='used with collect_past_sales, tells script to complete inspection after a certain address in the db')
    parser.add_argument('--update_sales_format', action='store_true')
    parser.add_argument('--update',              action='append',                   help='always update this field when parsing property, even if property itself is already in db')
    parser.add_argument('--threads',             type=int, default=1,               help='spawn n threads in parrallel, default is 1')
    parser.add_argument('--backup',              action='store_true',               help='backup main collection')
    parser.add_argument('--write_field',         type=str, default='',              help='field to write')
    parser.add_argument('--write_val',           type=str, default='',              help='value to write')
    parser.add_argument('--write_size',          type=str, default='',              help='size of bulk writes')
    
    args = parser.parse_args()
    tt = TruliaParser(username=args.username, password=args.password, host=args.host, port=args.port)
    tt.debug = args.debug
    tt.print_output = args.print_output
    if ( tt.debug ):
        print 'Parser instantiated'
    if ( args.write_size != '' ):
        tt.write_size = int( args.write_size ) 
    if ( args.update != None ):
        tt.property_update_array = args.update
    tt.threads = args.threads

    for i in range( tt.threads ):
        thread = threading.Thread(target=tt.worker, args=(args,i))
        thread.start()
    
