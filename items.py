# Funzioni Speciali Oggetti

from telegram import Update
from telegram.ext import ContextTypes
import mysql.connector
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

DB_USER = config.get('default', 'db_user')
DB_PSWD = config.get('default', 'db_pswd')
DB_HOST = config.get('default', 'db_host')

try:
    conn = mysql.connector.connect(
        user=DB_USER,
        host=DB_HOST,
        password=DB_PSWD,
        database="bot"
    )
    cur=conn.cursor(buffered=True)
except mysql.connector.Error as err:
    print("Errore MySQL: {}".format(err))

