from django.db.models import *
from mongoengine import *

class Properties( Document ):
    city = StringField(max_length = 30)
    neighborhood = StringField(max_length = 30)
    zip = IntField()
    sqft = IntField()
    sales = ListField(DictField())
    longitude = DecimalField()
    county = StringField(max_length = 30)
    trulia_link =  StringField(max_length = 100)
    state = IntField()
    address = StringField(max_length = 30)
    latitude = IntField()
    type = StringField(max_length = 30)
    parsed_past_sales = IntField()
    parsing_past_sales = IntField()
    num_beds  = IntField( default=0 )
    num_baths = IntField( default=0 )
    num_park = IntField( default=0 )
    type      = IntField( default=0 )
    trulia_id = IntField( default=0 )

