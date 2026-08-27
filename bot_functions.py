
import redis
from telebot.storage import StateRedisStorage

redis_client = redis.Redis(
    host = os.getenv()
)