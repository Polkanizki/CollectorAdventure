# Ricerca Oggetti

from telegram import Update
from telegram.ext import ContextTypes
import mysql.connector
import configparser
import time
import random

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

async def finder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur.execute("SELECT * FROM timer")
    rtimer = cur.fetchone()
    curt = round(time.time(), 2)
    if rtimer is None or (rtimer[0]+300.00 < curt):
        ## Send random item
        # Initialize variables
        user_id = update.effective_user.id
        username = update.effective_user.username
        chat_id = update.effective_chat.id

        ## Select initial phrase
        # randphr = random.randint(1, 2)
        randphr = 1
        cur.execute("SELECT phrase FROM messages WHERE id = {}".format(randphr))
        row1 = cur.fetchone()
        phrase = row1[0]

        ## Select item rarity
        # rarities = ['C', 'N', 'R', 'E', 'L', 'M', 'MS']
        # randrar = random.choices(rarities, weights=[80, 60, 50, 30, 20, 10, 5])
        rarities = ['C', 'N']
        randrar = random.choices(rarities, weights=[80, 60])

        ## Select item
        cur.execute("SELECT MAX(id) FROM oggetti WHERE rarity = '{}'".format(randrar[0]))
        row3 = cur.fetchone()
        randitem = random.randint(1, row3[0])
        cur.execute("SELECT nome FROM oggetti WHERE id = {}".format(randitem))
        item0 = cur.fetchone()
        item = item0[0].replace("'", "\'")

        ## Check inventory
        cur.execute("""SELECT * 
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_NAME = 'inventario_{}'""".format(user_id))
        inv = cur.fetchone()
        if inv is None:
            # Create new inventory
            cur.execute("""CREATE TABLE inventario_{} (
                        iditem INT FOREIGN KEY REFERENCES utenti(id),
                        name VARCHAR(30) NOT NULL,
                        rarity CHAR(1) NOT NULL,
                        qnt INT DEFAULT '0'
                        );""".format(user_id))
            conn.commit()
            print("Creazione inventario")
        else:
            if rtimer is None:
                # Set timer
                cur.execute("INSERT INTO timer (time) VALUES ({})".format(curt,))
                conn.commit()
                print("Inserimento timer")
            
            # Set new timer
            cur.execute("UPDATE timer SET time = '{}'".format(curt,))
            conn.commit()
            print("Set timer")

            # Register item
            cur.execute("SELECT qnt FROM inventario_{} WHERE iditem = {}".format(user_id, randitem))
            inv2 = cur.fetchone()
            if inv2 is None:
                cur.execute("""INSERT INTO inventario_{} 
                            (iditem, name, rarity, qnt)
                            VALUES
                            ({}, '{}', '{}', '1');""".format(user_id, randitem, item, randrar[0]))
                conn.commit()
                print("Inserimento in inventario")
            else:
                quantita = inv2[0]
                cur.execute("UPDATE inventario_{} SET qnt = {} WHERE iditem = {};".format(user_id, quantita+1, randitem))
                conn.commit()
                print("Aggiornamento inventario")
            await context.bot.send_message(chat_id, "@{} {} {}".format(username, phrase, item.replace("\\", "")))
            print("Tempo rimanente: {}s".format(int(300 - (curt - rtimer[0]))))
    else:
        print("Timer in cooldown")
        print("Tempo rimanente: {}s".format(int(300 - (curt - rtimer[0]))))

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_user.id
    msg = update.message.text
    pcmsg = msg.split(' ', 2)
    try:
        rar = pcmsg[1]
        obj = pcmsg[2]
    except IndexError:
        if chat_id == 134417022:
            await context.bot.send_message(chat_id, """Sintassi:\n/add [rarità] [oggetto]\nUsare l'escape""")
    else:
        if chat_id == 134417022:
            cur.execute("INSERT INTO oggetti (nome, rarity) VALUES ('{}', '{}')".format(obj, rar))
            conn.commit()
            
            await context.bot.send_message(chat_id, "{} [{}] registrato.".format(obj, rar))