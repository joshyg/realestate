from django.db.models import *
from mongoengine import *

# Create your models here.
class Properties( Document ):
    city = StringField(max_length = 30)
    neighborhood = StringField(max_length = 30)
    zip = IntField()
    sqftA= IntField()
    sales = ListField(EmbeddedDocumentField(Sale))
    longitude = DecimalField()
    county = StringField(max_length = 30)
    trulia_link =  StringField(max_length = 100)
    state = IntField()
    addressA = StringField(max_length = 30)
    latitude = IntField()
    type = StringField(max_length = 30)
    parsed_past_sales = IntField()

class Sale( Document ):
    price = IntField()
    day = IntField()
    month = IntField()
    year = IntField()
    date  = DateField()
