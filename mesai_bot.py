import json
import os
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pymongo import MongoClient

BOT_TOKEN = "8644328245:AAE-WcsSJ0-BHG9KaReQfh2FR4Cp8dIlLcM"
SAAT_UCRETI = 2000 / 8
TAM_MESAI_SAAT = 8
TAM_MESAI_UCRET = 2000
VERI_DOSYASI = "mesai_verileri.json"
TURKIYE = pytz.timezone('Europe/Istanbul')
UTC = pytz.UTC
MONGODB_URI = "mongodb+srv://emirhanksk:270325Ee.@telegram-bots.8l3uhpb.mongodb.net/?appName=telegram-bots"

client = MongoClient(MONGODB_URI)
db = client['telegram_bots']
mesai_collection = db['mesai']

class HealthCheck(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write('Mesai Bot Calisiyor!'.encode('utf-8'))
    
    def log_message(self, format, *args):
        pass

def web_sunucu():
    port = int(os.getenv('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheck)
    print(f"Web sunucu {port} portunda basladi")
    server.serve_forever()

def tr_saat():
    utc_now = datetime.now(UTC)
    return utc_now.astimezone(TURKIYE)

def veri_yukle():
    veriler = {}
    try:
        for kayit in mesai_collection.find():
            kullanici_id = kayit['kullanici_id']
            kayit_copy = kayit.copy()
            del kayit_copy['_id']
            del kayit_copy['kullanici_id']
            veriler[kullanici_id] = kayit_copy
    except:
        pass
    return veriler

def veri_kaydet(veri):
    try:
        for kullanici_id, bilgi in veri.items():
            mesai_collection.update_one(
                {'kullanici_id': kullanici_id},
                {'$set': {**bilgi, 'kullanici_id': kullanici_id}},
                upsert=True
            )
    except Exception as e:
        print(f"MongoDB kayit hatasi: {e}")
        
async def mesai_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kullanici = update.effective_user
    kullanici_id = str(kullanici.id)
    kullanici_adi = kullanici.first_name or kullanici.username or "Bilinmeyen"
    veri = veri_yukle()
    
    if kullanici_id in veri and veri[kullanici_id].get("aktif"):
        baslangic = veri[kullanici_id]["baslangic"]
        await update.message.reply_text(f"Zaten mesaidesin!\nBaslangic: {baslangic}")
        return
    
    simdi = tr_saat()
    veri[kullanici_id] = {
        "isim": kullanici_adi,
        "aktif": True,
        "baslangic": simdi.strftime("%Y-%m-%d %H:%M:%S"),
    }
    veri_kaydet(veri)
    
    await update.message.reply_text(
        f"{kullanici_adi}, mesain basladi!\n"
        f"Baslangic: {simdi.strftime('%d.%m.%Y %H:%M:%S')}\n"
        f"Tam mesai: {TAM_MESAI_SAAT} saat = {TAM_MESAI_UCRET} TL\n\n"
        f"Mesain bitince /cikis yaz."
    )

async def mesai_bitir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kullanici = update.effective_user
    kullanici_id = str(kullanici.id)
    kullanici_adi = kullanici.first_name or kullanici.username or "Bilinmeyen"
    veri = veri_yukle()
    
    if kullanici_id not in veri or not veri[kullanici_id].get("aktif"):
        await update.message.reply_text(f"{kullanici_adi}, aktif mesain bulunmuyor!")
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
    veri[kullanici_id]["aktif"] = False
    veri[kullanici_id]["son_bitis"] = bitis.strftime("%Y-%m-%d %H:%M:%S")
    veri[kullanici_id]["son_sure_saat"] = round(saat, 2)
    veri[kullanici_id]["son_ucret"] = round(ucret, 2)
    
    onceki_toplam = veri[kullanici_id].get("toplam_kazanc", 0)
    veri[kullanici_id]["toplam_kazanc"] = round(onceki_toplam + ucret, 2)
    veri_kaydet(veri)
    
    mesaj = f"{kullanici_adi}, mesain bitti!\n"
    mesaj += "=" * 30 + "\n"
    mesaj += f"Baslangic: {baslangic.strftime('%H:%M:%S')}\n"
    mesaj += f"Bitis: {bitis.strftime('%H:%M:%S')}\n"
    mesaj += f"Calisma: {tam_saat} saat {kalan_dakika} dakika\n"
    mesaj += "=" * 30 + "\n"
    mesaj += f"Kazanc: {ucret:.2f} TL\n"
    mesaj += "=" * 30 + "\n"
    mesaj += f"Toplam Kazanc: {veri[kullanici_id]['toplam_kazanc']:.2f} TL"
    
    await update.message.reply_text(mesaj)

async def durum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kullanici = update.effective_user
    kullanici_id = str(kullanici.id)
    kullanici_adi = kullanici.first_name or kullanici.username or "Bilinmeyen"
    veri = veri_yukle()
    
    if kullanici_id not in veri or not veri[kullanici_id].get("aktif"):
        await update.message.reply_text(f"{kullanici_adi}, su an mesaide degilsin.")
        return
    
    baslangic_str = veri[kullanici_id]["baslangic"]
    baslangic = datetime.strptime(baslangic_str, "%Y-%m-%d %H:%M:%S")
    baslangic = TURKIYE.localize(baslangic)
    
    simdi = tr_saat()
    fark = simdi - baslangic
    toplam_saniye = fark.total_seconds()
    saat = int(toplam_saniye / 3600)
    dakika = int((toplam_saniye % 3600) / 60)
    
    anlik_kazanc = (toplam_saniye / 3600) * SAAT_UCRETI
    kalan_saat = TAM_MESAI_SAAT - (toplam_saniye / 3600)
    
    if kalan_saat > 0:
        kalan_s = int(kalan_saat)
        kalan_d = int((kalan_saat - kalan_s) * 60)
        kalan_mesaj = f"Tam mesaiye kalan: {kalan_s} saat {kalan_d} dakika"
    else:
        kalan_mesaj = "Tam mesaiyi tamamladin!"
    
    mesaj = f"{kullanici_adi} - Mesai Durumu\n"
    mesaj += "=" * 30 + "\n"
    mesaj += "Mesaide\n"
    mesaj += f"Baslangic: {baslangic.strftime('%H:%M:%S')}\n"
    mesaj += f"Su an: {simdi.strftime('%H:%M:%S')}\n"
    mesaj += f"Gecen sure: {saat}s {dakika}d\n"
    mesaj += f"Anlik kazanc: {anlik_kazanc:.2f} TL\n"
    mesaj += kalan_mesaj
    
    await update.message.reply_text(mesaj)

async def rapor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    veri = veri_yukle()
    if not veri:
        await update.message.reply_text("Henuz kayitli mesai verisi yok.")
        return
    
    simdi = tr_saat()
    mesaj = "MESAI RAPORU\n"
    mesaj += f"Rapor Saati: {simdi.strftime('%d.%m.%Y %H:%M:%S')}\n"
    mesaj += "=" * 30 + "\n\n"
    
    for uid, bilgi in veri.items():
        isim = bilgi.get("isim", "Bilinmeyen")
        durum_text = "Mesaide" if bilgi.get("aktif") else "Mesaide degil"
        toplam = bilgi.get("toplam_kazanc", 0)
        
        mesaj += f"{isim}: {durum_text}\n"
        
        if bilgi.get("aktif"):
            baslangic_str = bilgi.get("baslangic", "")
            if baslangic_str:
                mesaj += f"  Baslangic: {baslangic_str[11:19]}\n"
        
        mesaj += f"  Toplam kazanc: {toplam:.2f} TL\n\n"
    
    await update.message.reply_text(mesaj)

async def yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = "KOMUTLAR\n"
    mesaj += "=" * 30 + "\n"
    mesaj += "/mesai - Mesaini baslat\n"
    mesaj += "/cikis - Mesaini bitir\n"
    mesaj += "/durum - Anlik mesai durumu\n"
    mesaj += "/rapor - Tum calisanlarin raporu\n"
    mesaj += "/yardim - Bu mesaji gosterir\n"
    mesaj += "=" * 30 + "\n"
    mesaj += f"8 saat = {TAM_MESAI_UCRET} TL | Saat basi = {SAAT_UCRETI:.2f} TL"
    
    await update.message.reply_text(mesaj)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    simdi = tr_saat()
    mesaj = "Merhaba! Mesai Takip Botuna hos geldin!\n\n"
    mesaj += f"Su anki Turkiye saati: {simdi.strftime('%d.%m.%Y %H:%M:%S')}\n\n"
    mesaj += "Mesaini baslatmak icin /mesai yaz.\n"
    mesaj += "Tum komutlar icin /yardim yaz."
    
    await update.message.reply_text(mesaj)

def main():
    threading.Thread(target=web_sunucu, daemon=True).start()
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mesai", mesai_baslat))
    app.add_handler(CommandHandler("cikis", mesai_bitir))
    app.add_handler(CommandHandler("durum", durum))
    app.add_handler(CommandHandler("rapor", rapor))
    app.add_handler(CommandHandler("yardim", yardim))
    
    simdi = tr_saat()
    print("Bot calisiyor...")
    print(f"Turkiye Saati: {simdi.strftime('%d.%m.%Y %H:%M:%S')}")
    app.run_polling()

if __name__ == "__main__":
    main()
