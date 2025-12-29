import os
import random
import string
import time
import logging
import asyncio
import names
from datetime import datetime
from typing import Optional, Dict
from dataclasses import dataclass

from curl_cffi import requests as curl_requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)
from telegram.constants import ParseMode

# 🔹 PORT BINDING
from aiohttp import web

BOT_TOKEN = "8229954158:AAGzZ5psj2K2osN2k5Na9pncnPE8u1ufiWU"
ADMIN_IDS = [7445191377]
COOLDOWN_SECONDS = 10

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

GET_EMAIL, GET_CODE = range(2)
user_cooldowns = {}

@dataclass
class AccountCredentials:
    username: str
    password: str
    email: str
    session_id: str
    csrf_token: str
    ds_user_id: str
    ig_did: str
    rur: str
    mid: str
    datr: str

    def to_formatted_message(self) -> str:
        return (
            f"✅ **Account Generated Successfully!**\n\n"
            f"👤 **Username:** `{self.username}`\n"
            f"🔑 **Password:** `{self.password}`\n"
            f"📧 **Email:** `{self.email}`\n\n"
            f"🍪 **Cookie Data:**\n"
            f"```\n"
            f"sessionid={self.session_id};\n"
            f"csrftoken={self.csrf_token};\n"
            f"ds_user_id={self.ds_user_id};\n"
            f"ig_did={self.ig_did};\n"
            f"rur={self.rur};\n"
            f"mid={self.mid};\n"
            f"datr={self.datr}\n"
            f"```"
        )

class InstagramAccountCreator:
    BASE_URL = "https://www.instagram.com"
    API_BASE_URL = f"{BASE_URL}/api/v1"

    def __init__(self):
        self.session = curl_requests.Session()
        self.session.impersonate = 'chrome110'
        self.headers = None
        self.ig_did = None

    def _extract(self, html, start, end):
        try:
            s = html.index(start) + len(start)
            e = html.index(end, s)
            return html[s:e]
        except:
            return None

    def generate_headers(self):
        ua = f'Mozilla/5.0 (Linux; Android {random.randint(10,13)}; SM-G9{random.randint(100,999)}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Mobile Safari/537.36'
        r1 = self.session.get(self.BASE_URL, headers={'user-agent': ua}, timeout=30)

        datr = r1.cookies.get('datr')
        csrf = r1.cookies.get('csrftoken')
        self.ig_did = r1.cookies.get('ig_did')
        mid = self._extract(r1.text, '{"mid":{"value":"', '",')

        r2 = self.session.get(
            self.BASE_URL,
            headers={'user-agent': ua, 'cookie': f'mid={mid}; csrftoken={csrf}'},
            timeout=30
        )
        app_id = self._extract(r2.text, 'APP_ID":"', '"')
        ajax = self._extract(r2.text, 'rollout_hash":"', '"')

        self.headers = {
            'authority': 'www.instagram.com',
            'content-type': 'application/x-www-form-urlencoded',
            'cookie': f'csrftoken={csrf}; mid={mid}; ig_did={self.ig_did}; datr={datr}',
            'origin': self.BASE_URL,
            'referer': f'{self.BASE_URL}/accounts/signup/email/',
            'user-agent': ua,
            'x-asbd-id': '198387',
            'x-csrftoken': csrf,
            'x-ig-app-id': app_id,
            'x-instagram-ajax': ajax,
            'x-requested-with': 'XMLHttpRequest',
        }

    def send_verification(self, email):
        mid = self.headers['cookie'].split('mid=')[1].split(';')[0]
        data = {'device_id': mid, 'email': email}
        resp = self.session.post(
            f'{self.API_BASE_URL}/accounts/send_verify_email/',
            headers=self.headers,
            data=data
        )
        return '"email_sent":true' in resp.text

    def validate_code(self, email, code):
        mid = self.headers['cookie'].split('mid=')[1].split(';')[0]
        data = {'code': code, 'device_id': mid, 'email': email}
        resp = self.session.post(
            f'{self.API_BASE_URL}/accounts/check_confirmation_code/',
            headers=self.headers,
            data=data
        )
        return resp.json().get('signup_code') if resp.json().get('status') == "ok" else None

    def create(self, email, signup_code):
        fname = names.get_first_name()
        res_suggest = self.session.post(
            f'{self.API_BASE_URL}/web/accounts/username_suggestions/',
            headers=self.headers,
            data={'email': email, 'name': fname}
        )

        try:
            suggestions = res_suggest.json().get('suggestions', [])
            username = random.choice(suggestions) if suggestions else (
                fname.lower() + str(random.randint(100,999))
            )
        except:
            username = fname.lower() + str(random.randint(100,999))

        pwd = f"{fname}@{random.randint(111, 999)}"
        mid = self.headers['cookie'].split('mid=')[1].split(';')[0]
        datr = self.headers['cookie'].split('datr=')[1].split(';')[0] if 'datr=' in self.headers['cookie'] else ""

        payload = {
            'enc_password': f'#PWD_INSTAGRAM_BROWSER:0:{round(time.time())}:{pwd}',
            'email': email,
            'username': username,
            'first_name': fname,
            'month': random.randint(1,12),
            'day': random.randint(1,28),
            'year': random.randint(1995,2003),
            'client_id': mid,
            'seamless_login_enabled': '1',
            'tos_version': 'row',
            'force_sign_up_code': signup_code,
        }

        resp = self.session.post(
            f'{self.API_BASE_URL}/web/accounts/web_create_ajax/',
            headers=self.headers,
            data=payload
        )

        if '"account_created":true' in resp.text:
            return AccountCredentials(
                username=username,
                password=pwd,
                email=email,
                session_id=resp.cookies.get('sessionid', ''),
                csrf_token=resp.cookies.get('csrftoken', ''),
                ds_user_id=resp.cookies.get('ds_user_id', ''),
                ig_did=self.ig_did,
                rur=resp.cookies.get('rur', ''),
                mid=mid,
                datr=datr
            )
        return None

def get_main_keyboard():
    return ReplyKeyboardMarkup([["Get Instagram Account"]], resize_keyboard=True)

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text(
        "👋 Welcome! Press the button to start.\n\n"
        "⏳ Users: Cooldown enabled\n"
        "⚡ Admins: No cooldown",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard()
    )

async def create_request(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("📧 Send the email address:")
    return GET_EMAIL

async def handle_email(u: Update, c: ContextTypes.DEFAULT_TYPE):
    email = u.message.text.strip()
    c.user_data['email'] = email

    creator = InstagramAccountCreator()
    c.user_data['creator'] = creator

    msg = await u.message.reply_text("⚙️ Sending code...")

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, creator.generate_headers)
    sent = await loop.run_in_executor(None, creator.send_verification, email)

    if sent:
        await msg.edit_text("📩 Enter the 6-digit code:")
        return GET_CODE

    await msg.edit_text("❌ Failed.")
    return ConversationHandler.END

async def handle_code(u: Update, c: ContextTypes.DEFAULT_TYPE):
    creator = c.user_data['creator']
    email = c.user_data['email']
    code = u.message.text.strip()

    loop = asyncio.get_running_loop()
    signup_code = await loop.run_in_executor(None, creator.validate_code, email, code)

    if not signup_code:
        await u.message.reply_text("❌ Invalid code.")
        return ConversationHandler.END

    acc = await loop.run_in_executor(None, creator.create, email, signup_code)
    if acc:
        await u.message.reply_text(acc.to_formatted_message(), parse_mode=ParseMode.MARKDOWN)

    return ConversationHandler.END

async def cancel(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("Cancelled.")
    return ConversationHandler.END

# 🔹 WEB SERVER
async def start_web():
    async def handle(_):
        return web.Response(text="Bot running")

    app = web.Application()
    app.router.add_get("/", handle)

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, "0.0.0.0", port).start()
    logger.info(f"Web server on {port}")

async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Get Instagram Account$"), create_request)],
        states={
            GET_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)],
            GET_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv)

    await start_web()
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
