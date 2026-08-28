from peewee import SqliteDatabase, Model, IntegerField, CharField, ForeignKeyField, FloatField, DateTimeField
from config import db_url
import datetime
from logger import bot_logger, log_error

db = SqliteDatabase(db_url)

class UnchangableFieldError(Exception):
    pass

class FieldNotFoundError(Exception):
    pass

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    user_id = IntegerField(primary_key=True)
    username = CharField(null=True)
    city = CharField(null=True)
    latitude = FloatField(null=True)
    longitude = FloatField(null=True)

class WeatherRequest(BaseModel):
    user = ForeignKeyField(User, backref='requests')
    city = CharField()
    latitude = FloatField()
    longitude = FloatField()
    requested_at = DateTimeField(default=datetime.datetime.now)

def create_model():
    db.create_tables(BaseModel.__subclasses__())

def create_user(user_id, database=db, username=None, city=None, latitude=None, longitude=None):
    try:
        user, created = User.get_or_create(
            user_id = user_id,
            username = username,
            city = city,
            latitude = latitude,
            longitude = longitude
        )
    except Exception as e:
        text = f'Error while creating user. {e}'
        log_error(bot_logger, user_id, text)

def update_user_data(user_id: int, datatype: str, data):
    try:
        datatype = datatype.lower()
        user = User.get(User.user_id == user_id)
        fields = {
            'username': user.username,
            'city': user.city,
            'lat': user.latitude,
            'lon': user.longitude
        }
        if datatype == 'user_id':
            raise UnchangableFieldError('That field is unchangable.')
        elif datatype not in fields.keys():
            raise FieldNotFoundError('That field does not exist.')
        changing_field = fields[datatype]
        changing_field = data
        user.save()
    except Exception as e:
        text = f'Error while updating user data. {e}'
        log_error(bot_logger, user_id, text)
        return

def get_user_data(user_id: int, datatype: str):
    try:
        user = User.get(User.user_id == user_id)
        fields = {
            'username': user.username,
            'city': user.city,
            'lat': user.latitude,
            'lon': user.longitude
        }
        if datatype not in fields.keys():
            raise FieldNotFoundError('That field does not exist.')
        out = fields[datatype]
        return out
    except Exception as e:
        text = f'Error while getting user data. {e}'

def create_request(user_id, city, lat, lon):
    try:
        user = User.get(User.user_id == user_id)
        WeatherRequest.create(
            user = user,
            city = city,
            latitude = lat,
            longitude = lon
        )
    except Exception as e:
        text = f'Error while creating weather request in table. {e}'
        log_error(bot_logger, user_id, text)
        return


