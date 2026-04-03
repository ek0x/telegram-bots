import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

BOT_TOKEN = "8638044446:AAFKqrfmvgIfUaqZM0Rxse8NW4Vr-OBpFTE"
VERI_DOSYASI = "bloke_verileri.json"

SAHIP, BANKA, TUTAR = range(3)

class HealthCheck(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write('✅ Bloke Bot Çalışıyor!'.encode('utf-8'))
    def log_message(self, format, *args):
        pass

def web_sunucu():
    port = int(os.getenv('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheck)
    print(f"🌐 Web sunucu {port} portunda başladı")
    server.serve_forever()

def veri_yukle():
    if os.path.exists(VERI_DOSYASI):
        try:
            with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def veri_kaydet(veri):
    with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💰 *Banka Bloke Takip Botu*\n\n"
        "📋 Komutlar:\n"
        "/ekle - Yeni bloke ekle\n"
        "/liste - Tüm blokeleri göster\n"
        "/sil - Bloke sil\n"
        "/toplam - Toplam tutarı göster\n"
        "/iptal - Devam eden işlemi iptal et",
        parse_mode='Markdown'
    )

async def ekle_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "📝 *Yeni Bloke Ekleme*\n\n"
        "👤 Banka sahibinin adını yazın:\n\n"
        "_İptal etmek için /iptal yazın_",
        parse_mode='Markdown'
    )
    return SAHIP

async def sahip_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sahip = update.message.text.strip()
    if not sahip:
        await update.message.reply_text("❌ Lütfen geçerli bir isim girin!")
        return SAHIP
    context.user_data['sahip'] = sahip
    await update.message.reply_text(
        f"✅ Sahip: *{sahip}*\n\n"
        f"🏦 Şimdi banka adını yazın:",
        parse_mode='Markdown'
    )
    return BANKA

async def banka_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    banka = update.message.text.strip()
    if not banka:
        await update.message.reply_text("❌ Lütfen geçerli bir banka adı girin!")
        return BANKA
    context.user_data['banka'] = banka
    await update.message.reply_text(
        f"✅ Banka: *{banka}*\n\n"
        f"💵 Son olarak bloke tutarını yazın:\n"
        f"_Örnek: 5000 veya 5000.50_",
        parse_mode='Markdown'
    )
    return TUTAR

async def tutar_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tutar_text = update.message.text.strip().replace(',', '.').replace(' ', '')
    try:
        tutar = float(tutar_text)
        if tutar <= 0:
            await update.message.reply_text("❌ Tutar sıfırdan büyük olmalı!")
            return TUTAR
        
        sahip = context.user_data.get('sahip')
        banka = context.user_data.get('banka')
        
        if not sahip or not banka:
            await update.message.reply_text("❌ Bir hata oluştu. Lütfen /ekle ile tekrar başlayın.")
            context.user_data.clear()
            return ConversationHandler.END
        
        veri = veri_yukle()
        yeni_kayit = {
            "id": max([k.get('id', 0) for k in veri], default=0) + 1,
            "sahip": sahip,
            "banka": banka,
            "tutar": tutar,
            "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ekleyen": update.effective_user.first_name or "Bilinmeyen"
        }
        
        veri.append(yeni_kayit)
        veri_kaydet(veri)
        
                await update.message.reply_text(
            f"Bloke Basariyla Eklendi!\n\n"
            f"ID: {yeni_kayit['id']}\n"
            f"Sahip: {sahip}\n"
            f"Banka: {banka}\n"
            f"Tutar: {tutar:,.2f} TL\n"
            f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
            
