from peewee import (SqliteDatabase, Model, IntegerField,
                    CharField, ForeignKeyField,
                    FloatField, DateTimeField, PrimaryKeyField,
                    AutoField, BooleanField)
from config import db_url
import datetime
from logger import bot_logger, log_error, log_info

db = SqliteDatabase(db_url)

class UnchangableFieldError(Exception):
    pass

class FieldNotFoundError(Exception):
    pass

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    register_date = DateTimeField(default=datetime.datetime.now)
    user_id = IntegerField(primary_key=True)
    chat_id = IntegerField(primary_key=True)
    username = CharField(null=True)
    city = CharField(null=True)
    is_subscribed = BooleanField(default=False)
    #TODO: > over-determined primary key user
    # ЕБАНАЯ ХУЙНЯ БЛЯЯЯЯЯДЬ!!!!!!!1
    # мне не нравится что я пишу. сука.
    subscriprion_time = CharField(null=True)

class WeatherRequest(BaseModel):
    user = ForeignKeyField(User, backref='requests')
    city = CharField()
    status = IntegerField()
    requested_at = DateTimeField(default=lambda: datetime.datetime.now)

class HelpRequest(BaseModel):
    id = AutoField(primary_key=True)
    user = ForeignKeyField(User, backref='help_requests')
    message = CharField(null=True)
    requested_at = DateTimeField(default=lambda: datetime.datetime.now)

def create_model():
    db.create_tables([User, WeatherRequest, HelpRequest], safe=True)

def create_user(user_id, chat_id, database=db, username=None, city=None, latitude=None, longitude=None):
    try:
        user, created = User.get_or_create(
            user_id = user_id,
            defaults={
                'username': username,
                'chat_id': chat_id,
                'city': city,
                'latitude': latitude,
                'longitude': longitude
            }
        )
        return user, created
    except Exception as e:
        text = f'Error while creating user. {e}'
        log_error(bot_logger, user_id, text)

def update_user_data(user_id: int, datatype: str, data):
    try:
        datatype = datatype.lower()
        fields = ['username', 'city', 'user_id', 'chat_id', 'username', 'city',
                  'is_subscribed', 'subscription_time']
        if not datatype in fields:
            raise FieldNotFoundError('That field does not exist.')
        query = User.update(**{datatype: data}).where(User.user_id == user_id)
        rows_updated = query.execute()
        if rows_updated == 0:
            raise User.DoesNotExist('User does not exist.')
        return rows_updated
    except User.DoesNotExist:
        text = f'Error while updating user data. User does not exist.'
        log_error(bot_logger, user_id, text)
        return None
    except Exception as e:
        text = f'Error while updating user data. {e}'
        log_error(bot_logger, user_id, text)
        return None
# def get_user_data(user_id: int, datatype: str):
#     try:
#         user = User.get(User.user_id == user_id)
#         fields = ['username', 'city', 'lat', 'lon']
#         if datatype not in fields:
#             raise FieldNotFoundError('That field does not exist.')
#         return getattr(user, datatype)
#     except Exception as e:
#         text = f'Error while getting user data. {e}'
#         log_error(bot_logger, user_id, text)
#         return None

def create_request(user_id, city, status):
    try:
        user = User.get(User.user_id == user_id)
        WeatherRequest.create(
            user = user,
            city = city,
            status = status
        )
    except Exception as e:
        text = f'Error while creating weather request in table. {e}'
        log_error(bot_logger, user_id, text)
        return

def create_help_request(user_id, message):
    try:
        user = User.get(User.user_id == user_id)
        HelpRequest.create(user = user, message = message)
        log_info(bot_logger, user_id, f'Новое сообщение для поддержки.')

    except Exception as e:
        text = f'Error while creating help request in table. {e}'
        log_error(bot_logger, user_id, text)
        return

