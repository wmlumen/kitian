import os
import json
import threading
from pathlib import Path

try:
    from telegram import Update
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False

BASE_DIR = Path(__file__).parent

app = None
telegram_token = None
_shared_state = None


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 KI - TIAN Bot activo.\n\n"
        "Comandos:\n"
        "/sistema - Estado del sistema\n"
        "/clima - Clima local\n"
        "/ayuda - Lista de comandos"
    )


async def cmd_sistema(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import psutil
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('C:\\').percent
    msg = (f"📊 Estado del sistema:\n"
           f"CPU: {cpu:.0f}%\n"
           f"RAM: {ram:.0f}%\n"
           f"Disco: {disk:.0f}%")
    await update.message.reply_text(msg)


async def cmd_clima(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ciudad = " ".join(context.args) if context.args else "San Lorenzo"
    try:
        import urllib.request
        data = urllib.request.urlopen(
            f"https://wttr.in/{ciudad.replace(' ','+')}?format=3&lang=es",
            timeout=8).read().decode("utf-8").strip()
        await update.message.reply_text(f"Clima: {data}")
    except Exception:
        await update.message.reply_text("No pude obtener el clima.")


async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Comandos KI - TIAN Bot:\n"
        "/sistema - CPU, RAM, Disco\n"
        "/clima [ciudad] - Clima local\n"
        "/ayuda - Esta ayuda\n"
        "También puede enviar texto libre."
    )


async def msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    if not texto:
        return
    try:
        if _shared_state:
            e, c, i = _shared_state.get()
            estado = e
        else:
            estado = "Activo"
        msg = f"🤖 KI - TIAN procesando: \"{texto}\"\nEstado: {estado}"
        await update.message.reply_text(msg)
    except Exception:
        await update.message.reply_text("Error procesando mensaje.")


def iniciar_bot(token, shared_state=None):
    global app, telegram_token, _shared_state
    if not HAS_TELEGRAM:
        return False
    telegram_token = token
    _shared_state = shared_state
    try:
        app = ApplicationBuilder().token(token).build()
        app.add_handler(CommandHandler("start", cmd_start))
        app.add_handler(CommandHandler("sistema", cmd_sistema))
        app.add_handler(CommandHandler("clima", cmd_clima))
        app.add_handler(CommandHandler("ayuda", cmd_ayuda))
        app.add_handler(MessageHandler(filters.TEXT, msg_handler))
        threading.Thread(target=lambda: app.run_polling(drop_pending_updates=True), daemon=True).start()
        return True
    except Exception:
        return False
