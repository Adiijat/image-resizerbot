import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from PIL import Image
import io
from flask import Flask
from threading import Thread

# --- CONFIGURATION ---
# Aapka Naya Token yahan add kar diya hai
BOT_TOKEN = "8498438723:AAGLUVLYro8JqeN4OHTrGs6VHq_KUaAS3UI"

# --- LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- FLASK SERVER (Render ko active rakhne ke liye) ---
app = Flask('')

@app.route('/')
def home():
    return "Resizer Bot is Alive!"

def run_http():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- BOT LOGIC ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Namaste! 🙏\n"
        "Main Image Resizer Bot hu.\n\n"
        "Mujhe koi bhi photo bhejein, main use resize ya compress kar dunga."
    )

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # User ne photo bheji, ab hum buttons dikhayenge
    file_id = update.message.photo[-1].file_id
    
    # File ID ko context me save kar lete hain
    context.user_data['last_image_id'] = file_id
    
    keyboard = [
        [InlineKeyboardButton("50% Size (Dimensions)", callback_data='resize_50')],
        [InlineKeyboardButton("Compress (Kam KB)", callback_data='compress')],
        [InlineKeyboardButton("Passport Size (No Crop)", callback_data='passport')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("Is photo ke sath kya karna hai?", reply_markup=reply_markup)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Loading hatao
    
    action = query.data
    
    if 'last_image_id' not in context.user_data:
        await query.edit_message_text("Purani photo expire ho gayi. Kripya dubara bhejein.")
        return

    await query.edit_message_text("Processing... ⏳")
    
    try:
        # Image download karein
        file_id = context.user_data['last_image_id']
        new_file = await context.bot.get_file(file_id)
        img_byte_arr = io.BytesIO()
        await new_file.download_to_memory(img_byte_arr)
        img_byte_arr.seek(0)
        
        original_img = Image.open(img_byte_arr)
        output_img = io.BytesIO()
        filename = "image.jpg"
        
        # --- LOGIC FOR RESIZING ---
        if action == 'resize_50':
            # Width aur Height ko aadha kar do
            width, height = original_img.size
            new_size = (width // 2, height // 2)
            resized_img = original_img.resize(new_size, Image.Resampling.LANCZOS)
            resized_img.save(output_img, format='JPEG')
            filename = "resized_50percent.jpg"
            
        elif action == 'compress':
            # Quality kam karke save karo (Size KB me kam ho jayega)
            original_img.save(output_img, format='JPEG', quality=40, optimize=True)
            filename = "compressed.jpg"
            
        elif action == 'passport':
            # Passport ratio (3.5 : 4.5) -> Approx 413x531 pixels
            # Note: Ye photo ko stretch karega, katega nahi (No Crop)
            resized_img = original_img.resize((413, 531), Image.Resampling.LANCZOS)
            resized_img.save(output_img, format='JPEG')
            filename = "passport_size.jpg"

        output_img.seek(0)
        
        # User ko wapas bhejo
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=output_img,
            filename=filename,
            caption="Ye lijiye aapki edit ki hui photo! ✅"
        )
        
    except Exception as e:
        # Agar message edit nahi ho sakta (kabhi kabhi hota hai), to naya message bhejo
        try:
            await query.edit_message_text(f"Error: {str(e)}")
        except:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Error aa gaya.")

if __name__ == '__main__':
    keep_alive()
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    application.add_handler(CallbackQueryHandler(button_click))
    
    print("Resizer Bot Running...")
    application.run_polling()
