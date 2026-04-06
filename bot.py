from flask import Flask
import os
import threading
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# 🔹 Flask app
web = Flask(__name__)

@web.route('/')
def home():
    return "Bot is running!"

# 🔹 Bot config
TOKEN = "8656250844:AAGCxiFYQBzWvHGyZOFkHepHlUoumBm_RC4"
ADMIN_ID = 5328734113

main_menu = [
    ["📁 Text to VCF", "📄 VCF to Text"],
    ["🔄 Merge VCF", "📦 Split Text"],
    ["⚓ Admin/Navy", "💎 Buy Premium"],
]

user_state = {}
vcf_data = {}

# 🔹 Load users
def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except:
        return {}

# 🔹 Save users
def save_users(data):
    with open("users.json", "w") as f:
        json.dump(data, f, indent=4)

# 🔹 Start command
def start(update: Update, context: CallbackContext):
    users = load_users()
    uid = str(update.message.from_user.id)

    if uid not in users:
        users[uid] = {"premium": False}
        save_users(users)

    update.message.reply_text(
        "🔥 ULTRA PRO BOT 🔥",
        reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    )

# 🔹 Handle TXT to VCF file
def handle_txt(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    file = update.message.document.get_file()
    filename = update.message.document.file_name

    if not filename.endswith(".txt"):
        update.message.reply_text("❌ Please send TXT file only")
        return

    path = f"{user_id}.txt"
    file.download(path)

    user_state[user_id] = {"step": "name", "file": path}
    update.message.reply_text("Enter Contact Name:")

def handle_text(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = update.message.text
    state = user_state.get(user_id)

    # -------- MENU --------
    if text == "📁 Text to VCF":
        update.message.reply_text("Send TXT file")
        return

    if text == "📄 VCF to Text":
        vcf_data[user_id] = {"files": []}
        user_state[user_id] = {"step": "upload"}
        update.message.reply_text(
            "📤 Upload VCF Files\n━━━━━━━━━━━━━━━\n"
            "📁 Send one or multiple .vcf files\n"
            "✅ Finish Type → /done"
        )
        return

# -------- TEXT → VCF FLOW --------
    if not state:
        return

    if state["step"] == "name":
        state["name"] = text
        state["step"] = "prefix"
        update.message.reply_text("Step 2️⃣ Enter file name:")
        return

    if state["step"] == "prefix":
        state["prefix"] = text
        state["step"] = "limit"
        update.message.reply_text("Step 3️⃣ Enter contacts per VCF:")
        return

    if state["step"] == "limit":
        try:
            limit = int(text)
        except:
            update.message.reply_text("Enter valid number")
            return

        with open(state["file"]) as f:
            numbers = f.read().splitlines()

        chunks = [numbers[i:i+limit] for i in range(0, len(numbers), limit)]

        for idx, chunk in enumerate(chunks):
            vcf = ""
            for i, num in enumerate(chunk):
                vcf += "BEGIN:VCARD\nVERSION:3.0\n"
                vcf += f"FN:{state['prefix']} {state['name']} {i+1}\n"
                vcf += f"TEL;TYPE=CELL:{num}\nEND:VCARD\n"

            filename = f"{state['prefix']}_{idx+1}.vcf"
            with open(filename, "w") as f:
                f.write(vcf)

            update.message.reply_document(open(filename, "rb"))
            os.remove(filename)

        update.message.reply_text("✅ Text to VCF Done!")
        user_state.pop(user_id)

# -------------------- VCF → TXT --------------------
def handle_vcf(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if user_state.get(user_id, {}).get("step") != "upload":
        return

    file = update.message.document
    if not file.file_name.endswith(".vcf"):
        update.message.reply_text("❌ Only .vcf file allowed")
        return

    tg_file = file.get_file()
    path = f"{user_id}_{len(vcf_data[user_id]['files'])}.vcf"
    tg_file.download(path)
    vcf_data[user_id]["files"].append(path)

    total = 0
    for f in vcf_data[user_id]["files"]:
        with open(f, encoding="utf-8", errors="ignore") as ff:
            for line in ff:
                if line.startswith("TEL"):
                    total += 1

    update.message.reply_text(
        f"📄 Extracting Numbers\n━━━━━━━━━━━━━━━\n"
        f"📁 Files Uploaded: {len(vcf_data[user_id]['files'])}\n"
        f"📊 Extracted: {total}\n"
        f"⏳ Status: Scanning...\n\n"
        f"📂 Keep sending files\n"
        f"✅ Finish Type → /done"
    )

# -------------------- DONE --------------------
def done(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if user_id not in vcf_data:
        update.message.reply_text("❌ No files uploaded")
        return

    user_state[user_id] = {"step": "txt_name"}
    update.message.reply_text(
        "📝 Enter the name for your .txt file:\nExample: ExtractedList"
    )

# -------------------- TXT NAME --------------------
def handle_txt_name(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    state = user_state.get(user_id)

    if not state or state.get("step") != "txt_name":
        return

    filename = update.message.text + ".txt"
    numbers = []

    for f in vcf_data[user_id]["files"]:
        with open(f, encoding="utf-8", errors="ignore") as ff:
            for line in ff:
                if line.startswith("TEL"):
                    numbers.append(line.split(":")[-1].strip())

    with open(filename, "w") as f:
        f.write("✅ Extracted Numbers\n━━━━━━━━━━━━━━━\n")
        for n in numbers:
            f.write(n + "\n")

    update.message.reply_document(open(filename, "rb"))
    update.message.reply_text("✅ Extraction Completed Successfully! 🎉")

    # cleanup
    for f in vcf_data[user_id]["files"]:
        os.remove(f)
    os.remove(filename)

    vcf_data.pop(user_id)
    user_state.pop(user_id)

# -------------------- RUN BOT --------------------
def run_bot():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("done", done))

    dp.add_handler(MessageHandler(Filters.document.mime_type("text/plain"), handle_txt))
    dp.add_handler(MessageHandler(Filters.document.mime_type("text/vcard"), handle_vcf))

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_txt_name))

    updater.start_polling()
    updater.idle()

# -------------------- MAIN --------------------
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()

    port = int(os.environ.get("PORT", 10000))
    web.run(host="0.0.0.0", port=port)