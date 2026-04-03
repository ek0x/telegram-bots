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
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Mesai Bot Calisiyor')
    def log_message(self, format, *args):
        pass

def web_sunucu():
    port = int(os.getenv('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheck)
    print("Web sunucu basladi")
    server.serve_forever()

def tr_saat():
    return datetime.now(UTC).astimezone(TURKIYE)

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
        await update.message.reply_text("Zaten mesaidesin!")
        return
    simdi = tr_saat()
    veri[kullanici_id] = {"isim": kullanici_adi, "aktif": True, "baslangic": simdi.strftime("%Y-%m-%d %H:%M:%S")}
    veri_kaydet(veri)
    await update.message.reply_text(f"{kullanici_adi}, mesain basladi!\nBaslangic: {simdi.strftime('%H:%M:%S')}")

async def mesai_bitir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kullanici = update.effective_user
    kullanici_id = str(kullanici.id)
    kullanici_adi = kullanici.first_name or kullanici.username or "Bilinmeyen"
    veri = veri_yukle()
    if kullanici_id not in veri or not veri[kullanici_id].get("aktif"):
        await update.message.reply_text("Aktif mesain bulunmuyor!")
        return
    baslangic = datetime.strptime(veri[kullanici_id]["baslangic"], "%Y-%m-%d %H:%M:%S")
    baslangic = TURKIYE.localize(baslangic)
    bitis = tr_saat()
    toplam_saniye = (bitis - baslangic).total_seconds()
    saat = toplam_saniye / 3600
    tam_saat = int(saat)
    dakika = int((toplam_saniye % 3600) / 60)
    ucret = saat * SAAT_UCRETI
    veri[kullanici_id]["aktif"] = False
    onceki_toplam = veri[kullanici_id].get("toplam_kazanc", 0)
    veri[kullanici_id]["toplam_kazanc"] = round(onceki_toplam + ucret, 2)
    veri_kaydet(veri)
    await update.message.reply_text(f"{kullanici_adi}, mesain bitti!\nCalisma: {tam_saat}s {dakika}d\nKazanc: {ucret:.2f} TL\nToplam: {veri[kullanici_id]['toplam_kazanc']:.2f} TL")

async def durum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kullanici_id = str(update.effective_user.id)
    veri = veri_yukle()
    if kullanici_id not in veri or not veri[kullanici_id].get("aktif"):
        await update.message.reply_text("Mesaide degilsin")
        return
    baslangic = TURKIYE.localize(datetime.strptime(veri[kullanici_id]["baslangic"], "%Y-%m-%d %H:%M:%S"))
    simdi = tr_saat()
    saniye = (simdi - baslangic).total_seconds()
    saat = int(saniye / 3600)
    dakika = int((saniye % 3600) / 60)
    kazanc = (saniye / 3600) * SAAT_UCRETI
    await update.message.reply_text(f"Mesaide\nSure: {saat}s {dakika}d\nKazanc: {kazanc:.2f} TL")

async def rapor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    veri = veri_yukle()
    if not veri:
        await update.message.reply_text("Veri yok")
        return
    mesaj = "RAPOR\n"
    for uid, bilgi in veri.items():
        durum = "Aktif" if bilgi.get("aktif") else "Pasif"
        toplam = bilgi.get("toplam_kazanc", 0)
        mesaj += f"{bilgi.get('isim')}: {durum} - {toplam:.2f} TL\n"
    await update.message.reply_text(mesaj)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Mesai Bot\nSaat: {tr_saat().strftime('%H:%M:%S')}\n/mesai - Baslat\n/cikis - Bitir\n/durum - Durum\n/rapor - Rapor")

def main():
    threading.Thread(target=web_sunucu, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mesai", mesai_baslat))
    app.add_handler(CommandHandler("cikis", mesai_bitir))
    app.add_handler(CommandHandler("durum", durum))
    app.add_handler(CommandHandler("rapor", rapor))
    print("Bot calisiyor")
    app.run_polling()

if __name__ == "__main__":
    main()
