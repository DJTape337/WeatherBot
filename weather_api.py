import requests
from logger import bot_logger, log_error, log_info
from config import base_url

def transform_date(date: str):
    out = date[-2:] + '-' + date[:2]
    return out

def get_forecast(user_id, lat, lon):
    params = {
        "latitude": lat,  # Ростов-на-Дону
        "longitude": lon,
        "current": "temperature_2m,wind_speed_10m,precipitation,precipitation_probability",
        "daily": "temperature_2m_max,temperature_2m_min,"
                 "temperature_2m_max,"
                 "wind_speed_10m_min,"
                 "wind_speed_10m_max,"
                 "precipitation_sum",
        "timezone": "auto",
        "forecast_days": 7,
    }
    try:
        response = requests.get(url=base_url, params=params, timeout=10)
        response.raise_for_status()
    except (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout) as e:
        log_error(bot_logger, user_id, e)
        return 'TimeoutError'
    except requests.exceptions.HTTPError as e:
        log_error(bot_logger, user_id, e)
        return 'StatusError'
    else:
        log_info(bot_logger, user_id, f'Запрос к серверу. Статус {response.status_code}')
    data = response.json()
    cur_data = data['current']
    daily_data = data['daily']
    daily_out = []
    for i in range(7):
        daily_out.append(tuple([transform_date(daily_data['time'][i][-5:]),
                               daily_data['temperature_2m_min'][i],
                               daily_data['temperature_2m_min'][i],
                               daily_data['temperature_2m_max'][i],
                               daily_data['wind_speed_10m_min'][i],
                               daily_data['wind_speed_10m_max'][i],
                               daily_data['precipitation_sum'][i]
                               ]))
    output = {
        'current': {
            'temp': int(cur_data['temperature_2m']),
            'wspeed': cur_data['wind_speed_10m'],
            'prec': cur_data['precipitation'],
            'precprob': cur_data['precipitation_probability']
        },
        'daily': daily_out
    }
    return output

# print(get_forecast(1, 55.7558, 37.6176,))
print(get_forecast(1, 55.7558, 37.6176))
