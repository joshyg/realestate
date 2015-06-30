#!/usr/local/bin/python2.7
import urllib2 as url
import datetime
import pymongo
from pymongo.errors import BulkWriteError
import csv
import re
import sh
import argparse
import time
import sys
import pprint
import copy
pp = pprint.PrettyPrinter(indent=4)

class ZillowParser( object ):
    def __init__( self, host='localhost', username='', password='', port=27017 ):
        self.client = pymongo.MongoClient(host=host, port=port)
        self.db = self.client['real_estate'] # will be created if it doesn't already exist
        self.db.authenticate(username, password)
        self.states = self.db['states'] # will be created if it doesn't already exist
        self.metros = self.db['metros'] # will be created if it doesn't already exist
        self.counties = self.db['counties'] # will be created if it doesn't already exist
        self.cities = self.db['cities'] # will be created if it doesn't already exist
        self.zips = self.db['zips'] # will be created if it doesn't already exist
        self.neighborhoods = self.db['neighborhoods'] # will be created if it doesn't already exist
        self.debug = False
        self.write_size = 50
        self.data_types = [ 'State', 'Metro', 'County', 'City', 'Zip', 'Neighborhood' ] 
        self.collections = [ 'states', 'metros', 'counties', 'cities', 'zips', 'neighborhoods' ] 
        self.collection_dict = dict(zip( self.data_types, self.collections ) )
        self.directory = ''


    def download_zips( self ):
        for file in self.data_types:
            sh.wget('-P', self.directory, 'http://files.zillowstatic.com/research/public/%s.zip'%file)

    def unzip_files( self ):
        for file in self.data_types:
            sh.unzip('%s/%s.zip'%(self.directory, file), '-d', self.directory)

    def get_data_set( self, file, data ):
        file_re = re.search('%s_(\S+).csv'%data, file)
        if ( file_re ):
            return str(file_re.group(1))
        file_re = re.search('(\S+)_%s(_Public)*.csv'%data, file)
        if ( file_re ):
            data_set = str(file_re.group(1))
            if ( file_re.group(2) ):
                data_set += '_Public'
            return data_set
        return ''
        

    def parse_files( self ):
        for data in self.data_types:
            documents = []
            dates_document = { 'dates_document' : 1 } # store all date arrays for a data type in a single document.  There should be one for each time series csv
            path = '%s/%s'%(self.directory,data)
            self.collection = self.__dict__[ self.collection_dict[data] ]
            for file in sh.ls(path):
                time_series = 'undetermined'
                file = file.replace('\n', '')
                if ( self.debug ):
                    print 'inspecting %s'%file

                # For csvs with a time series, data_set = time_series.
                # If the csv does not have a time series, it may have
                # ambiguous column names in which case I'll have to 
                # append the column name to the data_set name to make
                # it unique.
                data_set = self.get_data_set( file, data )
                if ( data_set != '' ):
                    if ( self.debug ):
                        print 'parsing %s'%data_set
                    fh = open( '%s/%s'%(path,file), 'r' )
                    fh_dr = csv.DictReader( fh )

                    # determine whether or not csv contains a time series
                    # if it does initialize a list in the document.
                    initial_document = {}
                    time_series_begun = False
                    for field in fh_dr.fieldnames:
                        if re.search('\d{4}-\d{2}', field):
                            if ( not time_series_begun ):
                                time_series_begun = True
                                time_series = data_set
                                initial_document = { '%s'%time_series : [] }
                                dates_document['%s_dates'%time_series] =  []
                            dates_document['%s_dates'%time_series].append( field )
                            
                            

                    # iterate over csv, populate time series as well as any other data
                    # each row in the csv is a document.
                    for line in fh_dr:
                        document = initial_document
                        # Note: the fieldnames list keeps the keys in order.  line.keys() or line.iteritems() does not
                        for field in fh_dr.fieldnames:
                            if ( time_series != 'undetermined' and re.search('\d{4}-\d{2}', field) ):
                                document[time_series].append( self.format( line[field] ) )
                            else:
                                document[field] = line[field].lower()

                        # without deepcopy we will keep overwriting the document reference
                        # and every item in documents will point to the last item appended
                        documents.append( copy.deepcopy( document  ) ) 
                        if ( len(documents) >= self.write_size ):
                            try:
                                self.save_documents( documents, time_series )
                                documents = []
                            except BulkWriteError as bwe:
                                pp.pprint(bwe.details)
                                sys.exit(1)

                # end of csv file
                print 'closing file'
                fh.close()
                if ( documents != [] ):
                    try:
                        self.save_documents( documents, time_series )
                        documents = []
                    except BulkWriteError as bwe:
                        pp.pprint(bwe.details)
                        sys.exit(1)
            # end of data type
            if ( self.debug ):
                print 'inserting dates document'
            self.collection.update_one( { 'dates_document' : 1 }, { '$set' :  dates_document } )


    def format( self, entry ):
        if ( re.search( '^ *\d+ *$', entry ) ):
            return int( entry )
        elif ( re.search('^ *\d+\.\d+ *$', entry) ):
            return float( entry )
        return entry

    def save_documents( self, documents, time_series ):
        requests = []
        for document in documents:
            print document['RegionName']
            if( time_series in document.keys() ):
                # In most cases, if the document is already there, then we are only updating the time series
                if ( self.debug ):
                    print 'updating'
                requests.append( pymongo.UpdateOne( {  'RegionName' : document['RegionName'] }, { '$set' : { time_series : document[time_series] } }, upsert=True ) )
            else:
                requests.append( pymongo.ReplaceOne( {  'RegionName' : document['RegionName'] }, document, upsert=True ) )
        if ( requests != [] ):
            if ( self.debug ):
                print 'BULK WRITE!'
            self.collection.bulk_write( requests )
    

if ( __name__ == '__main__' ):
    parser = argparse.ArgumentParser()
    parser.add_argument('--username',            type=str, default='',              help='username for db access')
    parser.add_argument('--password',            type=str, default='',              help='password for db access')
    parser.add_argument('--host',                type=str, default='localhost',     help='host for db access, default is localhost')
    parser.add_argument('--port',                type=str, default=27017,           help='port for db access')
    parser.add_argument('--debug',               action='store_true',               help='print debug statements')
    parser.add_argument('--download_zips',       action='store_true',               help='download zip files from zillow to directory specified in --directory or pwd if no directory specified')
    parser.add_argument('--unzip_files',         action='store_true',               help='unzip zip files downloaded from zillow in directory specified in --directory or pwd if no directory specified')
    parser.add_argument('--parse_files',         action='store_true',               help='parse csv files in unzipped directories under --directory ( or pwd ), populate/update db')
    parser.add_argument('--directory',           type=str, default='.',             help='directory to store/retrieve zip/csv files')

    args = parser.parse_args()
    zp = ZillowParser(username=args.username, password=args.password, host=args.host, port=int(args.port))
    zp.debug = args.debug
    zp.directory = args.directory
    if ( zp.debug ):
        print 'Parser instantiated'
    if ( args.download_zips ):
        zp.download_zips() 
    if ( args.unzip_files ):
        zp.unzip_files() 
    if ( args.parse_files ):
        zp.parse_files() 
