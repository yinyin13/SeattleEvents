import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


db_user = os.getenv('yinyin13')
db_pw = os.getenv('matildaH1311')
db_host = os.getenv('yinyin13-techin510-scraper.postgres.database.azure.com')
db_port = os.getenv('5432')
db_name = os.getenv('yinyin13')
conn_str = f'postgresql://{db_user}:{db_pw}@{db_host}:{db_port}/{db_name}'

def get_db_conn():
    conn = psycopg2.connect(conn_str)
    conn.autocommit = True
    return conn