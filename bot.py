from flask import Flask
import os
import threading
import telebot
import re
import time
from io import BytesIO
from telebot import types

# ================= CONFIGURATION =================
TOKEN = os.environ.get("BOT_TOKEN")   # Render Environment Variable
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

app = Flask(__name__)

# In-memory dictionary to store user states and data
user_data = {}

# ================= WEB SERVER =================
@app.route('/')
def home():
    return "VCF Bot Running Successfully ✅"

@app.route('/healthz')
def health():
    return "OK"

# ================= HELPER FUNCTIONS =================
def extract_numbers(text):
    return re.findall(r'\b\d{7,15}\b', text)

def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(
        types.KeyboardButton("Text to VCF"),
        types.KeyboardButton("VCF to Text")
    )
    return kb

# ================= COMMANDS =================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    user_data[uid] = {'state': 'IDLE'}

    load_msg = bot.send_message(uid, "<code>[>_] SYSTEM INITIATED...\nLoading Modules...\n[██░░░░░░░░] 20%</code>")
    time.sleep(0.5)

    bot.edit_message_text(
        "<code>[>_] BYPASSING PROTOCOLS...\nDecrypting Engine...\n[███████░░░] 70%</code>",
        chat_id=uid,
        message_id=load_msg.message_id
    )
    time.sleep(0.5)

    bot.edit_message_text(
        "<code>[>_] ACCESS GRANTED.\nBot Ready...\n[██████████] 100%</code>",
        chat_id=uid,
        message_id=load_msg.message_id
    )
    time.sleep(0.5)

    try:
        bot.delete_message(uid, load_msg.message_id)
    except:
        pass

    welcome = (
        "🔥 <b>WELCOME TO VCF CONVERTER BOT</b> 🔥\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "<code>[+] Status: Online</code>\n"
        "<code>[+] Mode: Render Web Service</code>\n\n"
        "👇 <i>Select a service below:</i>"
    )

    bot.send_message(uid, welcome, reply_markup=main_menu())

# ================= SERVICE ROUTER =================
@bot.message_handler(func=lambda m: m.text in ["Text to VCF", "VCF to Text"])
def service_router(message):
    uid = message.chat.id
    txt = message.text

    if txt == "Text to VCF":
        user_data[uid] = {'state': 'COLLECT_T2V', 'nums': [], 'msg_id': None}
        bot.send_message(
            uid,
            "📥 <b>Send Contacts</b>\n━━━━━━━━━━━━━━━\n"
            "📂 Send Numbers or Text File\n\n"
            "✅ Finish Type → <code>/done</code>",
            reply_markup=types.ReplyKeyboardRemove()
        )

    elif txt == "VCF to Text":
        user_data[uid] = {'state': 'COLLECT_V2T', 'nums': [], 'msg_id': None}
        bot.send_message(
            uid,
            "📤 <b>Upload VCF Files</b>\n━━━━━━━━━━━━━━━\n"
            "📁 Send one or multiple .vcf files\n\n"
            "✅ Finish Type → <code>/done</code>",
            reply_markup=types.ReplyKeyboardRemove()
        )

# ================= UNIVERSAL HANDLER =================
@bot.message_handler(content_types=['text', 'document'])
def universal_handler(message):
    uid = message.chat.id

    if uid not in user_data:
        return

    state = user_data[uid].get('state', 'IDLE')
    txt = message.text.strip() if message.text else ""

    if txt.lower() == "/cancel":
        user_data[uid] = {'state': 'IDLE'}
        bot.send_message(uid, "❌ Cancelled.", reply_markup=main_menu())
        return

    extracted = []

    # ---------- FILE READ ----------
    if message.document:
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded = bot.download_file(file_info.file_path)
            content = downloaded.decode("utf-8", errors="ignore")
            extracted = extract_numbers(content)
        except:
            extracted = []

    elif txt.lower() != "/done":
        extracted = extract_numbers(txt)

    # ==================================================
    # TEXT TO VCF
    # ==================================================
    if state == "COLLECT_T2V":

        if txt.lower() == "/done":
            total = len(user_data[uid]['nums'])

            if total == 0:
                bot.send_message(uid, "❌ No contacts collected.", reply_markup=main_menu())
                return

            user_data[uid]['state'] = "T2V_STEP_1"
            bot.send_message(uid, f"✅ Collected {total} numbers.")
            bot.send_message(uid, "1️⃣ Enter VCF File Name")
            return

        user_data[uid]['nums'].extend(extracted)
        total = len(user_data[uid]['nums'])

        msg = (
            f"📥 <b>Collecting Contacts</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📊 Total Added: <code>{total}</code>\n\n"
            f"Send More...\n"
            f"Finish → /done"
        )

        if not user_data[uid]['msg_id']:
            m = bot.send_message(uid, msg)
            user_data[uid]['msg_id'] = m.message_id
        else:
            try:
                bot.edit_message_text(msg, uid, user_data[uid]['msg_id'])
            except:
                pass

    elif state == "T2V_STEP_1":
        user_data[uid]['vname'] = txt
        user_data[uid]['state'] = "T2V_STEP_2"
        bot.send_message(uid, "2️⃣ Enter Contact Prefix Name")

    elif state == "T2V_STEP_2":
        user_data[uid]['prefix'] = txt
        user_data[uid]['state'] = "T2V_STEP_3"
        bot.send_message(uid, "3️⃣ Starting File Number")

    elif state == "T2V_STEP_3":
        user_data[uid]['vstart'] = int(txt) if txt.isdigit() else 1
        user_data[uid]['state'] = "T2V_STEP_4"
        bot.send_message(uid, "4️⃣ Starting Contact Number")

    elif state == "T2V_STEP_4":
        user_data[uid]['cstart'] = int(txt) if txt.isdigit() else 1
        user_data[uid]['state'] = "T2V_STEP_5"
        bot.send_message(uid, "5️⃣ Contacts Per File")

    elif state == "T2V_STEP_5":

        limit = int(txt) if txt.isdigit() else 50
        d = user_data[uid]

        nums = list(dict.fromkeys(d['nums']))
        v_idx = d['vstart']
        c_idx = d['cstart']

        bot.send_message(uid, f"🚀 Generating {len(nums)} Contacts")

        for i in range(0, len(nums), limit):
            chunk = nums[i:i+limit]

            if len(nums) > limit:
                fname = f"{d['vname']}{v_idx}.vcf"
            else:
                fname = f"{d['vname']}.vcf"

            vcf = ""

            for num in chunk:
                vcf += f"BEGIN:VCARD\nVERSION:3.0\nFN:{d['prefix']} {c_idx}\nTEL:{num}\nEND:VCARD\n"
                c_idx += 1

            bio = BytesIO(vcf.encode("utf-8"))
            bio.name = fname
            bot.send_document(uid, bio)

            v_idx += 1

        bot.send_message(uid, "✅ VCF Completed", reply_markup=main_menu())
        user_data[uid] = {'state': 'IDLE'}

    # ==================================================
    # VCF TO TEXT
    # ==================================================
    elif state == "COLLECT_V2T":

        if txt.lower() == "/done":
            total = len(user_data[uid]['nums'])

            if total == 0:
                bot.send_message(uid, "❌ No VCF collected.", reply_markup=main_menu())
                return

            user_data[uid]['state'] = "V2T_NAME"
            bot.send_message(uid, f"✅ Extracted {total} numbers")
            bot.send_message(uid, "📝 Enter TXT File Name")
            return

        user_data[uid]['nums'].extend(extracted)
        total = len(user_data[uid]['nums'])

        msg = (
            f"📄 <b>Extracting Numbers</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📊 Total: <code>{total}</code>\n\n"
            f"Send More VCF Files...\n"
            f"Finish → /done"
        )

        if not user_data[uid]['msg_id']:
            m = bot.send_message(uid, msg)
            user_data[uid]['msg_id'] = m.message_id
        else:
            try:
                bot.edit_message_text(msg, uid, user_data[uid]['msg_id'])
            except:
                pass

    elif state == "V2T_NAME":

        nums = list(dict.fromkeys(user_data[uid]['nums']))
        file_text = "\n".join(nums)

        bio = BytesIO(file_text.encode("utf-8"))
        bio.name = txt + ".txt"

        bot.send_document(uid, bio, caption="✅ Numbers Extracted")
        bot.send_message(uid, "✅ Completed", reply_markup=main_menu())

        user_data[uid] = {'state': 'IDLE'}

# ================= RUN BOT =================
def run_bot():
    while True:
        try:
            print("Bot Running...")
            bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
        except Exception as e:
            print("Error:", e)
            time.sleep(5)

threading.Thread(target=run_bot).start()

# ================= START WEB =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)