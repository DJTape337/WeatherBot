from peewee import SqliteDatabase, Model, IntegerField, CharField
from config import db_url

db = SqliteDatabase(db_url)

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    user_id = IntegerField(primary_key=True)
    username = CharField(null=True)
    city = CharField(null=True)
    latitude = IntegerField(null=True)
    longitude = IntegerField(null=True)



