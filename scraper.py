import re
import json
import datetime
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup
import itertools

from db import get_db_conn


base_url = "https://visitseattle.org/events/page/"
pages = 35
events_ls = []
URL_LIST_FILE = './data/links.json'
URL_DETAIL_FILE = './data/data.json'

def list_links():
    for pg in range (1, pages+1):
        url = f'{base_url}{pg}'
        res = requests.get(url)

        soup = BeautifulSoup(res.text, "html.parser")
        selector = "div.search-result-preview > div > h3 > a"

        a_eles = soup.select(selector)

        events_ls.append([x['href'] for x in a_eles])
    
    events_ls = list(itertools.chain.from_iterable(events_ls))
    json.dump(events_ls, open(URL_LIST_FILE, 'w'))

def get_detail_page():
    links = json.load(open(URL_LIST_FILE, 'r'))
    data = []
    for link in links:
        try:
            row = {}
            res = requests.get(link).text
            soup = BeautifulSoup(res, 'html.parser')
            row['title'] = soup.find(class_="page-title").text
            datetime_venue = soup.find('h4').text.split(" | ")
            row['date'] = datetime.datetime.strptime(datetime_venue[0], '%m/%d/%Y').replace(tzinfo=ZoneInfo('America/Los_Angeles')).isoformat()
            row['venue'] = datetime_venue[1].strip() # remove leading/trailing whitespaces
            metas = re.findall(r'<a href=".+?" class="button big medium black category">(.+?)</a>', res.text)
            row['category'] = soup.find(class_="button big medium black category").text
            row['location'] = soup.select_one('a.button.big.medium.black.category[href*=event_regions]').text
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
        location TEXT
    );
    '''
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(q)
    
    urls = json.load(open(URL_LIST_FILE, 'r'))
    data = json.load(open(URL_DETAIL_FILE, 'r'))
    for url, row in zip(urls, data):
        q = '''
        INSERT INTO events (url, title, date, venue, category, location)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (url) DO NOTHING;
        '''
        cur.execute(q, (url, row['title'], row['date'], row['venue'], row['category'], row['location']))

if __name__ == '__main__':
    list_links()
    get_detail_page()
    insert_to_pg()