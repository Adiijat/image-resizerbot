import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from PIL import Image
import io
from flask import Flask
from threading import Thread

# --- CONFIGURATION ---
BOT_TOKEN = "8498438723:AAGLUVLYro8JqeN4OHTrGs6VHq_KUaAS3UI"

# --- LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- FLASK SERVER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Alive!"

def run_http():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- HELPER FUNCTION ---
def compress_image_to_size(image, target_kb):
    min_quality = 5
    current_quality = 95
    
    img_byte_arr = io.BytesIO()
    
    if image.mode != 'RGB':
        image = image.convert('RGB')
        
    image.save(img_byte_arr, format='JPEG', quality=current_quality)
    
    # Loop: Jab tak size target se bada hai, quality girate raho
    while img_byte_arr.tell() > target_kb * 1024 and current_quality > min_quality:
        img_byte_arr = io.BytesIO()
        current_quality -= 5
        image.save(img_byte_arr, format='JPEG', quality=current_quality)
        
    img_byte_arr.seek(0)
    return img_byte_arr, current_quality

# --- BOT LOGIC ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🖼️ Resize/Compress Image", callback_data='ask_photo')],
        [InlineKeyboardButton("📂 Image to PDF", callback_data='mode_pdf')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Namaste! Option select karein:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == 'mode_pdf':
        await query.edit_message_text("PDF ke liye yahan jayein: @Pdftoolzbot")
        return
        
    elif data == 'ask_photo':
        context.user_data['waiting_for_photo'] = True
        await query.edit_message_text("Theek hai, ab apni **Photo** bhejein jise resize karna hai.")
        return

    if 'last_photo' not in context.user_data:
        await query.edit_message_text("Session expire ho gaya. Phir se photo bhejein.")
        return

    await query.edit_message_text("Processing... ⏳")
    
    try:
        file_id = context.user_data['last_photo']
        new_file = await context.bot.get_file(file_id)
        img_byte_arr = io.BytesIO()
        await new_file.download_to_memory(img_byte_arr)
        img_byte_arr.seek(0)
        
        image = Image.open(img_byte_arr)
        output_img = io.BytesIO()
        filename = "processed.jpg"
        caption = "Done!"
        
        if image.mode != 'RGB':
            image = image.convert('RGB')

        if data == 'qual_50':
            image.save(output_img, format='JPEG', quality=50, optimize=True)
            caption = "Quality reduced to 50%."
            
        elif data == 'qual_25':
            image.save(output_img, format='JPEG', quality=25, optimize=True)
            caption = "Quality reduced to 25%."
            
        elif data.startswith('target_'):
            target_kb = int(data.split('_')[1])
            output_img, final_q = compress_image_to_size(image, target_kb)
            caption = f"Target: Under {target_kb}KB (Final Quality: {final_q}%)"
            
        output_img.seek(0)
        
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=output_img,
            filename=filename,
            caption=caption
        )
        
        context.user_data.pop('last_photo', None)
        
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error: {str(e)}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.photo[-1].file_id
    context.user_data['last_photo'] = file_id
    
    # --- Updated Options Menu (20 KB Added) ---
    keyboard = [
        [InlineKeyboardButton("📉 Quality 50%", callback_data='qual_50'),
         InlineKeyboardButton("📉 Quality 75%", callback_data='qual_25')],
         
        [InlineKeyboardButton("💾 Under 20 KB", callback_data='target_20'),
         InlineKeyboardButton("💾 Under 50 KB", callback_data='target_50')],
         
        [InlineKeyboardButton("💾 Under 100 KB", callback_data='target_100'),
         InlineKeyboardButton("💾 Under 500 KB", callback_data='target_500')],
         
        [InlineKeyboardButton("💾 Under 1 MB", callback_data='target_1000')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Is photo ko kitna chhota karna hai? Select karein:", 
        reply_markup=reply_markup
    )

if __name__ == '__main__':
    keep_alive()
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("Bot Running...")
    application.run_polling()
