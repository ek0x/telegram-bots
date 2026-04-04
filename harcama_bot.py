import os
from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from pymongo import MongoClient
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import io

BOT_TOKEN = "8723144601:AAGv3MIamyyi-bg39Vsv3zWvQQ-K42FFwYY"
MONGODB_URI = "mongodb+srv://emirhanksk:270325Ee.@telegram-bots.8l3uhpb.mongodb.net/?appName=telegram-bots"
TURKIYE = pytz.timezone('Europe/Istanbul')

client = MongoClient(MONGODB_URI)
db = client['telegram_bots']
harcama_collection = db['harcama']

KATEGORI, TUTAR, ACIKLAMA = range(3)

KATEGORILER = {
    "kaptan": "👨‍✈️ Kaptan",
    "raptor": "🦖 Raptor",
    "set": "💳 Set Ödemesi",
    "ortak": "🏘️ Ortak Gider"
}

class HealthCheck(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Harcama Bot Calisiyor')
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
    def log_message(self, format, *args):
        pass

def web_sunucu():
    port = int(os.getenv('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheck)
    print("Web sunucu basladi")
    server.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = "📊 Harcama Takip Botu\n\n"
    mesaj += "Komutlar:\n"
    mesaj += "/harcama - Yeni harcama ekle\n"
    mesaj += "/liste - Bugunun harcamalari\n"
    mesaj += "/toplam - Toplam harcama\n"
    mesaj += "/excel - Excel dosyasi indir\n"
    await update.message.reply_text(mesaj)

async def harcama_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👨‍✈️ Kaptan", callback_data="kat_kaptan"),
         InlineKeyboardButton("🦖 Raptor", callback_data="kat_raptor")],
        [InlineKeyboardButton("💳 Set Ödemesi", callback_data="kat_set"),
         InlineKeyboardButton("🏘️ Ortak Gider", callback_data="kat_ortak")],
        [InlineKeyboardButton("❌ İptal", callback_data="kat_iptal")]
    ]
    await update.message.reply_text("Kategori sec:", reply_markup=InlineKeyboardMarkup(keyboard))
    return KATEGORI

async def kategori_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "kat_iptal":
        await query.edit_message_text("Iptal edildi.")
        return ConversationHandler.END
    
    kategori_key = query.data.replace("kat_", "")
    context.user_data['kategori'] = kategori_key
    
    await query.edit_message_text(f"Kategori: {KATEGORILER[kategori_key]}\n\nTutari yaz (TL):")
    return TUTAR

async def tutar_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tutar = float(update.message.text.replace(',', '.').replace(' ', ''))
        if tutar <= 0:
            await update.message.reply_text("Tutar sifirdan buyuk olmali!")
            return TUTAR
        context.user_data['tutar'] = tutar
        await update.message.reply_text("Aciklama yaz (veya 'yok' yaz):")
        return ACIKLAMA
    except:
        await update.message.reply_text("Gecersiz tutar! Tekrar dene:")
        return TUTAR

async def aciklama_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    aciklama = update.message.text.strip()
    if aciklama.lower() == 'yok':
        aciklama = "-"
    
    kategori_key = context.user_data['kategori']
    tutar = context.user_data['tutar']
    simdi = datetime.now(TURKIYE)
    kullanici = update.effective_user.first_name or update.effective_user.username or "Bilinmeyen"
    
    try:
        harcama = {
            "tarih": simdi.strftime("%Y-%m-%d"),
            "saat": simdi.strftime("%H:%M"),
            "kategori": KATEGORILER[kategori_key],
            "tutar": tutar,
            "aciklama": aciklama,
            "ekleyen": kullanici,
            "timestamp": simdi
        }
        
        harcama_collection.insert_one(harcama)
        
        mesaj = "✅ Harcama Kaydedildi!\n\n"
        mesaj += f"📁 Kategori: {KATEGORILER[kategori_key]}\n"
        mesaj += f"💰 Tutar: {tutar:,.2f} TL\n"
        mesaj += f"📝 Aciklama: {aciklama}\n"
        mesaj += f"📅 Tarih: {simdi.strftime('%d.%m.%Y %H:%M')}\n"
        mesaj += f"👤 Ekleyen: {kullanici}\n\n"
        mesaj += "✅ Veritabanina eklendi!"
        
        await update.message.reply_text(mesaj)
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {e}")
    
    context.user_data.clear()
    return ConversationHandler.END

async def iptal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Iptal edildi.")
    return ConversationHandler.END

async def liste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        bugun = datetime.now(TURKIYE).strftime("%Y-%m-%d")
        harcamalar = list(harcama_collection.find({"tarih": bugun}))
        
        if not harcamalar:
            await update.message.reply_text("Bugun harcama yok.")
            return
        
        mesaj = f"📋 BUGUNUN HARCAMALARI\nTarih: {datetime.now(TURKIYE).strftime('%d.%m.%Y')}\n"
        mesaj += "=" * 30 + "\n\n"
        
        toplam = 0
        for h in harcamalar:
            mesaj += f"{h['kategori']}\n"
            mesaj += f"💰 {h['tutar']:,.2f} TL\n"
            mesaj += f"📝 {h['aciklama']}\n"
            mesaj += f"👤 {h['ekleyen']} - {h['saat']}\n\n"
            toplam += h['tutar']
        
        mesaj += f"💎 TOPLAM: {toplam:,.2f} TL"
        await update.message.reply_text(mesaj)
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {e}")

async def toplam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        harcamalar = list(harcama_collection.find())
        
        if not harcamalar:
            await update.message.reply_text("Henuz harcama yok.")
            return
        
        bugun = datetime.now(TURKIYE).strftime("%Y-%m-%d")
        
        bugun_toplam = sum(h['tutar'] for h in harcamalar if h.get('tarih') == bugun)
        genel_toplam = sum(h['tutar'] for h in harcamalar)
        
        kategoriler = {}
        for h in harcamalar:
            kat = h['kategori']
            kategoriler[kat] = kategoriler.get(kat, 0) + h['tutar']
        
        mesaj = "📊 HARCAMA ÖZETİ\n"
        mesaj += "=" * 30 + "\n\n"
        mesaj += f"📅 Bugun: {bugun_toplam:,.2f} TL\n"
        mesaj += f"📅 Toplam: {genel_toplam:,.2f} TL\n\n"
        mesaj += "📁 Kategoriler:\n"
        for kat, tut in sorted(kategoriler.items(), key=lambda x: x[1], reverse=True):
            mesaj += f"{kat}: {tut:,.2f} TL\n"
        
        await update.message.reply_text(mesaj)
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {e}")

async def excel_indir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        harcamalar = list(harcama_collection.find().sort("timestamp", -1))
        
        if not harcamalar:
            await update.message.reply_text("Henuz harcama yok.")
            return
        
        csv_data = "Tarih,Saat,Kategori,Tutar,Aciklama,Ekleyen\n"
        
        for h in harcamalar:
            tarih_formatted = datetime.strptime(h['tarih'], "%Y-%m-%d").strftime("%d.%m.%Y")
            csv_data += f"{tarih_formatted},{h['saat']},{h['kategori']},{h['tutar']},{h['aciklama']},{h['ekleyen']}\n"
        
        csv_file = io.BytesIO(csv_data.encode('utf-8-sig'))
        csv_file.name = f"harcamalar_{datetime.now(TURKIYE).strftime('%d%m%Y')}.csv"
        
        await update.message.reply_document(
            document=csv_file,
            caption="📊 Harcama Raporu\n\nBu dosyayi Excel ile acabilirsin!"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {e}")

def main():
    threading.Thread(target=web_sunucu, daemon=True).start()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    harcama_handler = ConversationHandler(
        entry_points=[CommandHandler('harcama', harcama_baslat)],
        states={
            KATEGORI: [CallbackQueryHandler(kategori_sec)],
            TUTAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutar_al)],
            ACIKLAMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, aciklama_al)],
        },
        fallbacks=[CommandHandler('iptal', iptal)],
        allow_reentry=True,
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(harcama_handler)
    app.add_handler(CommandHandler("liste", liste))
    app.add_handler(CommandHandler("toplam", toplam))
    app.add_handler(CommandHandler("excel", excel_indir))
    
    print("Harcama Takip Botu calisiyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
