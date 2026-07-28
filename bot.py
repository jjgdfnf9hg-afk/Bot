import os
import random
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ================== CONFIGURAZIONE ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

SITE_URL = "https://fornitoreeuro.store"
CONTACT_URL = "https://t.me/fornitoreeuro"
# ====================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

user_captcha = {}
admin_reply_to = {}


def generate_captcha():
    a = random.randint(12, 35)
    b = random.randint(5, 15)
    return a, b, a - b


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    a, b, result = generate_captcha()
    user_captcha[user_id] = result

    await update.message.reply_text(
        f"🔐 *Verifica di sicurezza*\n\n"
        f"Risolvi questa operazione per continuare:\n\n"
        f"👉  *{a} − {b} = ?*\n\n"
        f"Scrivi solo il numero del risultato.",
        parse_mode="Markdown"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    text = update.message.text.strip()

    # Admin sta rispondendo a un utente
    if user_id == ADMIN_ID and user_id in admin_reply_to:
        target_id = admin_reply_to[user_id]
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"📩 *Risposta dal supporto:*\n\n{text}",
                parse_mode="Markdown"
            )
            await update.message.reply_text("✅ Messaggio inviato all'utente.")
        except Exception as e:
            await update.message.reply_text(f"❌ Errore nell'invio: {e}")
        finally:
            del admin_reply_to[user_id]
        return

    # CAPTCHA
    if user_id in user_captcha:
        try:
            answer = int(text)
        except ValueError:
            await update.message.reply_text("❌ Inserisci solo un numero.")
            return

        if answer == user_captcha[user_id]:
            del user_captcha[user_id]

            keyboard = [
                [InlineKeyboardButton("🌐 Visita il sito", url=SITE_URL)],
                [InlineKeyboardButton("📩 Contattami", url=CONTACT_URL)],
                [InlineKeyboardButton("⚠️ Se sei limitato scrivimi qui", callback_data="limited")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            caption = (
                "✅ *Verifica completata!*\n\n"
                "Scegli un'opzione qui sotto:"
            )

            try:
                with open("welcome.jpg", "rb") as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption=caption,
                        parse_mode="Markdown",
                        reply_markup=reply_markup
                    )
            except FileNotFoundError:
                await update.message.reply_text(
                    caption,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
        else:
            a, b, result = generate_captcha()
            user_captcha[user_id] = result
            await update.message.reply_text(
                f"❌ Risposta sbagliata.\n\n"
                f"Prova di nuovo:\n👉 *{a} − {b} = ?*",
                parse_mode="Markdown"
            )
        return

    # Messaggio da utente (dopo captcha)
    if user_id != ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("💬 Rispondi a questo utente", callback_data=f"reply_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        forward_text = (
            f"📨 *Nuovo messaggio*\n\n"
            f"👤 {user.first_name or ''} {user.last_name or ''}\n"
            f"🔗 @{user.username or 'nessuno'}\n"
            f"🆔 `{user_id}`\n\n"
            f"💬 {text}"
        )

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=forward_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            await update.message.reply_text(
                "✅ Messaggio inviato.\nTi risponderemo il prima possibile."
            )
        except Exception as e:
            logger.error(e)
            await update.message.reply_text("❌ Errore nell'invio. Riprova più tardi.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "limited":
        await query.message.reply_text(
            "✍️ *Scrivi pure qui sotto il tuo messaggio.*\n"
            "Ti risponderò il prima possibile.",
            parse_mode="Markdown"
        )
        return

    if data.startswith("reply_"):
        target_id = int(data.split("_")[1])
        admin_reply_to[query.from_user.id] = target_id

        await query.message.reply_text(
            f"✍️ Stai rispondendo all'utente `{target_id}`.\n\n"
            f"Scrivi ora il messaggio che vuoi inviargli:",
            parse_mode="Markdown"
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN non impostato!")
    if ADMIN_ID == 0:
        raise ValueError("ADMIN_ID non impostato!")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    print("✅ Bot avviato correttamente...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
