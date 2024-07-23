# Main

import research
# import items
import logging
import configparser
import mysql.connector
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
from ptb_pagination import InlineKeyboardPaginator
import math

config = configparser.ConfigParser()
config.read('config.ini')

BOT_TOKEN = config.get('default', 'bot_token')
DB_USER = config.get('default', 'db_user')
DB_PSWD = config.get('default', 'db_pswd')
DB_HOST = config.get('default', 'db_host')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger('httpx').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        keyboard = [
            [InlineKeyboardButton('ℹ️ Info', callback_data='info')],
            [InlineKeyboardButton('🎒 Inventario', callback_data='inv')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        cur.execute('SELECT * FROM utenti WHERE id = {}'.format(update.effective_user.id))
        row = cur.fetchone()
        cur.execute("""SELECT * 
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_NAME = 'inventario_{}'""".format(update.effective_user.id))
        inv = cur.fetchone()
        if inv is None:
            # Create new inventory
            cur.execute("""CREATE TABLE inventario_{} (
                        iditem INT FOREIGN KEY REFERENCES utenti(id),
                        name VARCHAR(30) NOT NULL,
                        rarity CHAR(1) NOT NULL,
                        qnt INT DEFAULT '0'
                        );""".format(update.effective_user.id))
            conn.commit()
            print("Creazione inventario")
        if row is None:
            # print(row[0]) per stampare l'ID
            cur.execute('INSERT INTO utenti (id) VALUES ("%s")', (update.effective_user.id,))
            conn.commit()

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Ciao *{}*".format(update.effective_chat.first_name),
            parse_mode='MarkdownV2',
            reply_markup=reply_markup
        )

async def anyreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chatid = update.effective_chat.id
    await context.bot.send_message(chatid, "Per giocare avvia il bot in privato")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "*📦Adventure Bot*\n\n/start \\- Avvia il bot\n/help \\- Mostra questo menu"

    if update.effective_user.id == 134417022:
        text = text + "\n\n*⚠️COMANDI ADMIN⚠️*\n/add \\- Aggiunge un oggetto al database\n/reset \\- Resetta il timer \\(a volte\\)"

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode='MarkdownV2'
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'info':
        await query.edit_message_text(text='#01 Success')
    elif query.data == 'close':
        await query.delete_message()

async def inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    MAX_PAGE_SIZE = 10
    query = update.callback_query
    await query.answer()

    cur.execute("""SELECT * 
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_NAME = 'inventario_{}'""".format(query.from_user.id))
    cinv = cur.fetchone()

    cur.execute("SELECT * FROM inventario_{}".format(query.from_user.id))
    inv = cur.fetchall()

    paginator = InlineKeyboardPaginator(
        math.ceil(len(inv)/MAX_PAGE_SIZE),
        data_pattern='page#{page}'
    )

    keyboard = [[InlineKeyboardButton('❌ Chiudi', callback_data='close')]]
    paginator.add_after(keyboard)
    
    text = "🎒 Inventario di @{}:\n\n".format(query.from_user.username)
    for i in inv:
        text = text + f"\\- {i[1]} \\[{i[2]}\\] x{i[3]}\n"

    if cinv is not None and inv != []:
        await query.edit_message_text( # type: ignore
            text=text,
            reply_markup=paginator.markup,
            parse_mode='MarkdownV2'
        )
    else:
        await query.edit_message_text("Inventario vuoto😱")

async def inventory_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    MAX_PAGE_SIZE = 10
    query = update.callback_query
    await query.answer()

    cur.execute("SELECT * FROM inventario_{} WHERE iditem".format(query.from_user.id))
    inv = cur.fetchall()

    page = int(query.data.split('#')[1])

    paginator = InlineKeyboardPaginator(
        math.ceil(len(inv)/MAX_PAGE_SIZE),
        current_page=page,
        data_pattern='page#{page}'
    )

    keyboard = [[InlineKeyboardButton('❌ Chiudi', callback_data='close')]]
    paginator.add_after(keyboard)

    text = "🎒 Inventario di @{}:\n\n".format(query.from_user.username)
    for i in range((page-1)*10, len(inv)):
        text = text + f"\\- {list(inv[i])[1]} \\[{list(inv[i])[2]}\\] x{list(inv[i])[3]}\n"

    await query.edit_message_text(
        text=f"{text}",
        reply_markup=paginator.markup,
        parse_mode='MarkdownV2'
    )

async def rtime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    userid = update.message.from_user.id
    if userid == 134417022:
        try:
            cur.execute("DELETE FROM timer;")
            conn.commit()
            print("Timer resettato")
        except mysql.connector.Error as err:
            print(err)

## Chiusura Database
def dbclose():
    cur.close()
    conn.close()

## Main
if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', help)
    inv_handler = CallbackQueryHandler(inventory, pattern='^inv')
    inv_button_handler = CallbackQueryHandler(inventory_callback, pattern='^page#')
    buttons_handler = CallbackQueryHandler(button)
    finder_handler = MessageHandler((filters.TEXT & filters.ChatType.GROUPS) & ~filters.COMMAND, research.finder)
    c_add_handler = CommandHandler('add', research.add)
    rtime_handler = CommandHandler('reset', rtime)
    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(inv_handler)
    application.add_handler(inv_button_handler)
    application.add_handler(buttons_handler)
    application.add_handler(finder_handler)
    application.add_handler(c_add_handler)
    application.add_handler(rtime_handler)

    application.run_polling(timeout=20)
    dbclose()