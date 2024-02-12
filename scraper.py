import re
import json
import datetime
from zoneinfo import ZoneInfo
import html

import requests

from db import get_db_conn


URL = 'https://visitseattle.org/events/page/'
URL_LIST_FILE = './data/links.json'
URL_DETAIL_FILE = './data/data.json'

def list_links():
    res = requests.get(URL + '1/')
    last_page_no = int(re.findall(r'bpn-last-page-link"><a href=".+?/page/(\d+?)/.+" title="Navigate to last page">', res.text)[0])

    links = []
    for page_no in range(1, last_page_no + 1):
        res = requests.get(URL + str(page_no) + '/')
        links.extend(re.findall(r'<h3 class="event-title"><a href="(https://visitseattle.org/events/.+?/)" title=".+?">.+?</a></h3>', res.text))

    json.dump(links, open(URL_LIST_FILE, 'w'))

def get_weather_data(location_query):
    location_query = f'{location_query}, Seattle'
    location_url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': location_query,
        'format': 'json',
    }
    response = requests.get(location_url, params=params)
    location_data = response.json()

    if location_data:
        latitude = location_data[0]['lat']
        longitude = location_data[0]['lon']

        # Use latitude and longitude to query weather API
        weather_api_url = f"https://api.weather.gov/points/{latitude},{longitude}"
        weather_response = requests.get(weather_api_url)
        weather_data = weather_response.json()

        forecast_url = weather_data['properties']['forecast']
        detailed_forecast_url = weather_data['properties']['forecastGridData']
        res = requests.get(forecast_url)
        weather_forecast_data = res.json()

        # Extracting short forecast
        short_forecast = weather_forecast_data.get('properties', {}).get('periods', [{}])[0].get('shortForecast', '')

        # Fetch more detailed forecast data to get min, max temperature, and wind chill
        grid_res = requests.get(detailed_forecast_url)
        grid_data = grid_res.json()
        min_temperature = grid_data.get('properties', {}).get('minTemperature', {}).get('values', [{}])[0].get('value', '')
        max_temperature = grid_data.get('properties', {}).get('maxTemperature', {}).get('values', [{}])[-1].get('value', '')
        wind_chill = grid_data.get('properties', {}).get('windChill', {}).get('values', [{}])[0].get('value', '')

        return short_forecast, min_temperature, max_temperature, wind_chill, latitude, longitude

    return None, None, None, None


def get_detail_page():
    links = json.load(open(URL_LIST_FILE, 'r'))
    data = []
    for link in links:
        try:
            row = {}
            res = requests.get(link)
            row['title'] = html.unescape(re.findall(r'<h1 class="page-title" itemprop="headline">(.+?)</h1>', res.text)[0])
            datetime_venue = re.findall(r'<h4><span>.*?(\d{1,2}/\d{1,2}/\d{4})</span> \| <span>(.+?)</span></h4>', res.text)[0]
            row['date'] = datetime.datetime.strptime(datetime_venue[0], '%m/%d/%Y').replace(tzinfo=ZoneInfo('America/Los_Angeles')).isoformat()
            row['venue'] = datetime_venue[1].strip() # remove leading/trailing whitespaces
            metas = re.findall(r'<a href=".+?" class="button big medium black category">(.+?)</a>', res.text)
            row['category'] = html.unescape(metas[0])
            row['location'] = metas[1]

            location_query = row['location']

            if '/' in location_query:
                location_query = location_query.split(' / ')[0].strip()
                location_query = [f'{location_query}, Seattle']

            # Fetch weather data
            short_forecast, min_temperature, max_temperature, wind_chill, latitude, longitude = get_weather_data(location_query)
            row['short_forecast'] = short_forecast
            row['min_temperature'] = min_temperature
            row['max_temperature'] = max_temperature
            row['wind_chill'] = wind_chill
            row['latitude'] = latitude
            row['longitude'] = longitude

            data.append(row)
        except IndexError as e:
            print(f'Error: {e}')
            print(f'Link: {link}')
    json.dump(data, open(URL_DETAIL_FILE, 'w'))


def insert_to_pg():
    q = '''
    CREATE TABLE IF NOT EXISTS events (
        url TEXT PRIMARY KEY,
        title TEXT,
        date TIMESTAMP WITH TIME ZONE,
        venue TEXT,
        category TEXT,
        location TEXT,
        short_forecast TEXT,
        min_temperature TEXT,
        max_temperature TEXT,
        wind_chill TEXT,
        latitude TEXT,
        longitude TEXT
    );
    '''
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(q)
    
    urls = json.load(open(URL_LIST_FILE, 'r'))
    data = json.load(open(URL_DETAIL_FILE, 'r'))
    for url, row in zip(urls, data):
        q = '''
        INSERT INTO events (url, title, date, venue, category, location, short_forecast, min_temperature, max_temperature, wind_chill, latitude, longitude)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (url) DO NOTHING;
        '''
        cur.execute(q, (url, row['title'], row['date'], row['venue'], row['category'], row['location'], row['short_forecast'], row['min_temperature'], row['max_temperature'], row['wind_chill'], row['latitude'], row['longitude']))

if __name__ == '__main__':
    list_links()
    get_detail_page()
    insert_to_pg()