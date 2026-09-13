import requests
from logger import bot_logger, log_error
from config import base_url

def get_forecast(user_id,
                 latitude,
                 longitude,
                 moment='daily',
                 timezone='auto'):
    values = 'temperature_2m,wind_speed_10m, precipitation_sum'
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'wind_speed_unit': 'ms',
        'timezone': timezone
    }
    try:
        if moment == 'current':
            params['current_weather'] = True
        elif moment == 'hourly':
            params['hourly'] = values
        elif moment == 'daily':
            params['daily'] = values,
            params['forecast_days'] = 7
        else:
            raise ValueError('Ошибка. Некорректный запрос.')
    except ValueError as e:
        log_error(bot_logger, user_id, e)
        return None
    try:
        response = requests.get(url=base_url, params=params, timeout=10)
        response.raise_for_status()

    except requests.exceptions.HTTPError as e:
        log_error(bot_logger, user_id, e)
        return None
    data = response.json()
    temp = data[moment]['temperature_2m']
    wspeed = data[moment]['wind_speed_10m']
    perc = data[moment]['precipitation_sum']
    return temp, wspeed, perc

print(get_forecast(1, 55.7558, 37.6176,))

