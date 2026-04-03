import json
import os
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

BOT_TOKEN = "8644328245:AAE-WcsSJ0-BHG9KaReQfh2FR4Cp8dIlLcM"
SAAT_UCRETI = 2000 / 8
TAM_MESAI_SAAT = 8
TAM_MESAI_UCRET = 2000
VERI_DOSYASI = "mesai_verileri.json"
TURKIYE = pytz.timezone('Europe/Istanbul')
UTC = pytz.UTC

class HealthCheck(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write('✅ Mesai Bot Çalışıyor!'.encode('utf-8'))
    def log_message(self, format, *args):
        pass

def web_sunucu():
    port = int(os.getenv('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheck)
    print(f"🌐 Web sunucu {port} portunda başladı")
    server.serve_forever()

def tr_saat():
    utc_now = datetime.now(UTC)
    return utc_now.astimezone(TURKIYE)

def veri_yukle():
    if os.path.exists(VERI_DOSYASI):
        with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def veri_kaydet(veri):
    with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)

async def mesai_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kullanici = update.effective_user
    kullanici_id = str(kullanici.id)
    kullanici_adi = kullanici.first_name or kullanici.username or "Bilinmeyen"
    veri = veri_yukle()
    
    if kullanici_id in veri and veri[kullanici_id].get("aktif"):
        baslangic = veri[kullanici_id]["baslangic"]
        await update.message.reply_text(
            f"⚠️ {kullanici_adi}, zaten mesaidesin!\n🕐 Başlangıç: {baslangic}"
        )
        return
    
    simdi = tr_saat()
    veri[kullanici_id] = {
        "isim": kullanici_adi,
        "aktif": True,
        "baslangic": simdi.strftime("%Y-%m-%d %H:%M:%S"),
    }
    veri_kaydet(veri)
    
    await update.message.reply_text(
        f"✅ {kullanici_adi}, mesain başladı!\n"
        f"🕐 Başlangıç: {simdi.strftime('%d.%m.%Y %H:%M:%S')}\n"
        f"📌 Tam mesai: {TAM_MESAI_SAAT} saat = {TAM_MESAI_UCRET}₺\n\n"
        f"Mesain bitince /cikis yaz."
    )

async def mesai_bitir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kullanici = update.effective_user
    kullanici_id = str(kullanici.id)
    kullanici_adi = kullanici.first_name or kullanici.username or "Bilinmeyen"
    veri = veri_yukle()
    
    if kullanici_id not in veri or not veri[kullanici_id].get("aktif"):
        await update.message.reply_text(
            f"⚠️ {kullanici_adi}, aktif mesain bulunmuyor!\n"
            f"Önce /mesai yazarak mesaini başlat."
        )
        return
    
    baslangic_str = veri[kullanici_id]["baslangic"]
    baslangic = datetime.strptime(baslangic_str, "%Y-%m-%d %H:%M:%S")
    baslangic = TURKIYE.localize(baslangic)
    
    bitis = tr_saat()
    fark = bitis - baslangic
    toplam_saniye = fark.total_seconds()
    saat = toplam_saniye / 3600
    tam_saat = int(saat)
    kalan_dakika = int((toplam_saniye % 3600) / 60)
    
    ucret = saat * SAAT_UCRETI
        await update.message.reply_text(
        f"🔴 {kullanici_adi}, mesain bitti!\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 Başlangıç : {baslangic.strftime('%H:%M:%S')}\n"
        f"🕐 Bitiş     : {bitis.strftime('%H:%M:%S')}\n"
        f"⏱️ Çalışma   : {tam_saat} saat {kalan_dakika} dakika\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Kazanç    : {ucret:.2f}₺\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Toplam Kazanç: {veri[kullanici_id]['toplam_kazanc']:.2f}₺"
    )
