import os
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from pymongo import MongoClient
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

BOT_TOKEN = os.getenv('BOT_TOKEN')
MONGODB_URI = os.getenv('MONGODB_URI')
TURKIYE = pytz.timezone('Europe/Istanbul')

client = MongoClient(MONGODB_URI)
db = client['telegram_bots']
banka_set_collection = db['banka_set']

ISIM, BANKALAR = range(2)

class HealthCheck(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Banka Set Bot Calisiyor')
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
    mesaj = "🏦 Banka Set Takip Botu\n\n"
    mesaj += "Komutlar:\n"
    mesaj += "/ekle - Yeni kisi + bankalar ekle\n"
    mesaj += "/liste - Tum kisileri listele\n"
    mesaj += "/detay - Kisinin bankalari\n"
    mesaj += "/sil - Kisi sil\n"
    mesaj += "/topla - Toplam istatistik\n"
    await update.message.reply_text(mesaj)

async def ekle_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("👤 Isim Soyisim yazin:\n\n_Iptal icin /iptal yazin_")
    return ISIM

async def isim_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    isim = update.message.text.strip()
    if not isim or len(isim) < 3:
        await update.message.reply_text("❌ Lutfen gecerli bir isim girin!")
        return ISIM
    
    mevcut = banka_set_collection.find_one({"isim_lower": isim.lower()})
    if mevcut:
        await update.message.reply_text(f"⚠️ {isim} zaten kayitli!\n\n/detay {isim} ile gorebilirsin.")
        return ConversationHandler.END
    
    context.user_data['isim'] = isim
    mesaj = f"✅ Isim: {isim}\n\n"
    mesaj += "🏦 Simdi bankalari yazin:\n"
    mesaj += "Her satira bir banka yazin ve tek mesaj olarak gonderin.\n\n"
    mesaj += "Ornek:\n"
    mesaj += "Ziraat Bankasi\n"
    mesaj += "Is Bankasi\n"
    mesaj += "Garanti BBVA"
    
    await update.message.reply_text(mesaj)
    return BANKALAR
    
async def banka_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    metin = update.message.text.strip()
    
    satirlar = metin.split('\n')
    bankalar = [s.strip() for s in satirlar if s.strip()]
    
    if len(bankalar) == 0:
        await update.message.reply_text("❌ En az 1 banka yazin!")
        return BANKALAR
    
    isim = context.user_data['isim']
    simdi = datetime.now(TURKIYE)
    ekleyen = update.effective_user.first_name or update.effective_user.username or "Bilinmeyen"
    
    kayit = {
        "isim": isim,
        "isim_lower": isim.lower(),
        "bankalar": bankalar,
        "tarih": simdi.strftime("%Y-%m-%d %H:%M:%S"),
        "ekleyen": ekleyen
    }
    
    banka_set_collection.insert_one(kayit)
    
    mesaj = "✅ Kaydedildi!\n\n"
    mesaj += f"👤 {isim}\n"
    mesaj += f"🏦 {len(bankalar)} Banka:\n\n"
    for i, banka in enumerate(bankalar, 1):
        mesaj += f"{i}. {banka}\n"
    mesaj += f"\n📅 {simdi.strftime('%d.%m.%Y %H:%M')}\n"
    mesaj += f"👤 Ekleyen: {ekleyen}"
    
    await update.message.reply_text(mesaj)
    context.user_data.clear()
    return ConversationHandler.END
    
    bankalar = context.user_data.get('bankalar', [])
    bankalar.append(metin)
    context.user_data['bankalar'] = bankalar
    
    await update.message.reply_text(
        f"✅ Eklendi: {metin}\n\n"
        f"📊 Toplam: {len(bankalar)} banka\n\n"
        f"Devam edin veya /tamam yazin"
    )
    return BANKALAR

async def iptal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Iptal edildi.")
    return ConversationHandler.END

async def liste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kisiler = list(banka_set_collection.find().sort("isim", 1))
    
    if not kisiler:
        await update.message.reply_text("📋 Henuz kayitli kisi yok.")
        return
    
    mesaj = "📋 KAYITLI KISILER\n"
    mesaj += "=" * 30 + "\n\n"
    
    toplam_banka = 0
    for k in kisiler:
        banka_sayisi = len(k['bankalar'])
        toplam_banka += banka_sayisi
        mesaj += f"👤 {k['isim']}\n"
        mesaj += f"   🏦 {banka_sayisi} banka\n"
        mesaj += f"   📅 {k['tarih'][:10]}\n\n"
    
    mesaj += "=" * 30 + "\n"
    mesaj += f"📊 Toplam: {len(kisiler)} kisi\n"
    mesaj += f"🏦 Toplam: {toplam_banka} banka"
    
    await update.message.reply_text(mesaj)

async def detay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Kullanim: /detay Isim Soyisim\n\n"
            "Ornek: /detay Ahmet Yilmaz"
        )
        return
    
    isim = " ".join(context.args)
    kisi = banka_set_collection.find_one({"isim_lower": isim.lower()})
    
    if not kisi:
        await update.message.reply_text(f"❌ {isim} bulunamadi!")
        return
    
    mesaj = f"👤 {kisi['isim']}\n"
    mesaj += "=" * 30 + "\n\n"
    mesaj += f"🏦 Bankalar ({len(kisi['bankalar'])}):\n\n"
    
    for i, banka in enumerate(kisi['bankalar'], 1):
        mesaj += f"{i}. {banka}\n"
    
    mesaj += f"\n📅 Kayit: {kisi['tarih'][:10]}\n"
    mesaj += f"👤 Ekleyen: {kisi.get('ekleyen', 'Bilinmeyen')}"
    
    await update.message.reply_text(mesaj)

async def sil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Kullanim: /sil Isim Soyisim\n\n"
            "Ornek: /sil Ahmet Yilmaz"
        )
        return
    
    isim = " ".join(context.args)
    sonuc = banka_set_collection.delete_one({"isim_lower": isim.lower()})
    
    if sonuc.deleted_count > 0:
        await update.message.reply_text(f"✅ {isim} silindi!")
    else:
        await update.message.reply_text(f"❌ {isim} bulunamadi!")

async def topla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kisiler = list(banka_set_collection.find())
    
    if not kisiler:
        await update.message.reply_text("📊 Henuz veri yok.")
        return
    
    toplam_kisi = len(kisiler)
    toplam_banka = sum(len(k['bankalar']) for k in kisiler)
    
    banka_dagilim = {}
    for k in kisiler:
        for banka in k['bankalar']:
            banka_dagilim[banka] = banka_dagilim.get(banka, 0) + 1
    
    mesaj = "📊 GENEL ISTATISTIK\n"
    mesaj += "=" * 30 + "\n\n"
    mesaj += f"👥 Toplam Kisi: {toplam_kisi}\n"
    mesaj += f"🏦 Toplam Banka: {toplam_banka}\n"
    mesaj += f"📊 Ortalama: {toplam_banka/toplam_kisi:.1f} banka/kisi\n\n"
    
    if banka_dagilim:
        mesaj += "🏦 En Cok Kullanilan Bankalar:\n"
        for banka, sayi in sorted(banka_dagilim.items(), key=lambda x: x[1], reverse=True)[:5]:
            mesaj += f"  • {banka}: {sayi} kisi\n"
    
    await update.message.reply_text(mesaj)

def main():
    threading.Thread(target=web_sunucu, daemon=True).start()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    ekle_handler = ConversationHandler(
        entry_points=[CommandHandler('ekle', ekle_baslat)],
        states={
            ISIM: [MessageHandler(filters.TEXT & ~filters.COMMAND, isim_al)],
            BANKALAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, banka_al)],
        },
        fallbacks=[CommandHandler('iptal', iptal)],
        allow_reentry=True,
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ekle_handler)
    app.add_handler(CommandHandler("liste", liste))
    app.add_handler(CommandHandler("detay", detay))
    app.add_handler(CommandHandler("sil", sil))
    app.add_handler(CommandHandler("topla", topla))
    
    print("Banka Set Takip Botu calisiyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
