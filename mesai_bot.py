import os
from datetime import datetime, timedelta
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pymongo import MongoClient

BOT_TOKEN = os.getenv('BOT_TOKEN')
MONGODB_URI = os.getenv('MONGODB_URI')
SAAT_UCRETI = 2000 / 8
TAM_MESAI_SAAT = 8
TAM_MESAI_UCRET = 2000
TURKIYE = pytz.timezone('Europe/Istanbul')
UTC = pytz.UTC

client = MongoClient(MONGODB_URI)
db = client['telegram_bots']
mesai_collection = db['mesai']
gecmis_collection = db['mesai_gecmis']

class HealthCheck(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Mesai Bot Calisiyor')
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

def tr_saat():
    return datetime.now(UTC).astimezone(TURKIYE)

def veri_yukle():
    veriler = {}
    try:
        for kayit in mesai_collection.find():
            kullanici_id = kayit['kullanici_id']
            kayit_copy = kayit.copy()
            del kayit_copy['_id']
            del kayit_copy['kullanici_id']
            veriler[kullanici_id] = kayit_copy
    except Exception as e:
        print(f"Veri yukleme hatasi: {e}")
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
        print(f"Veri kayit hatasi: {e}")

def gecmis_kaydet(kullanici_id, isim, baslangic_str, bitis_str, sure_saat, ucret):
    try:
        tarih = bitis_str[:10]
        gecmis_collection.update_one(
            {
                'kullanici_id': kullanici_id,
                'tarih': tarih
            },
            {
                '$set': {
                    'kullanici_id': kullanici_id,
                    'isim': isim,
                    'tarih': tarih,
                    'baslangic': baslangic_str,
                    'bitis': bitis_str,
                    'sure_saat': round(sure_saat, 2),
                    'ucret': round(ucret, 2)
                }
            },
            upsert=True
        )
        print(f"Gecmis kaydedildi: {isim} - {tarih}")
    except Exception as e:
        print(f"Gecmis kayit hatasi: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    simdi = tr_saat()
    mesaj = "Merhaba! Mesai Takip Botuna hos geldin!\n\n"
    mesaj += f"Su anki Turkiye saati: {simdi.strftime('%d.%m.%Y %H:%M:%S')}\n\n"
    mesaj += "Mesaini baslatmak icin /mesai yaz.\n"
    mesaj += "Tum komutlar icin /yardim yaz."
    await update.message.reply_text(mesaj)

async def mesai_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kullanici = update.effective_user
    kullanici_id = str(kullanici.id)
    kullanici_adi = kullanici.first_name or kullanici.username or "Bilinmeyen"
    veri = veri_yukle()

    if kullanici_id in veri and veri[kullanici_id].get("aktif"):
        baslangic = veri[kullanici_id]["baslangic"]
        await update.message.reply_text(
            f"Zaten mesaidesin!\n"
            f"Baslangic: {baslangic}"
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
        await update.message.reply_text(
            f"{kullanici_adi}, aktif mesain bulunmuyor!\n"
            f"Oncelikle /mesai ile mesai baslat."
        )
        return

    baslangic_str = veri[kullanici_id]["baslangic"]
    baslangic = TURKIYE.localize(datetime.strptime(baslangic_str, "%Y-%m-%d %H:%M:%S"))
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

    gecmis_kaydet(
        kullanici_id=kullanici_id,
        isim=kullanici_adi,
        baslangic_str=baslangic_str,
        bitis_str=bitis.strftime("%Y-%m-%d %H:%M:%S"),
        sure_saat=round(saat, 2),
        ucret=round(ucret, 2)
    )

    mesaj = f"{kullanici_adi}, mesain bitti!\n"
    mesaj += "=" * 30 + "\n"
    mesaj += f"Baslangic : {baslangic.strftime('%H:%M:%S')}\n"
    mesaj += f"Bitis     : {bitis.strftime('%H:%M:%S')}\n"
    mesaj += f"Calisma   : {tam_saat} saat {kalan_dakika} dakika\n"
    mesaj += "=" * 30 + "\n"
    mesaj += f"Kazanc    : {ucret:.2f} TL\n"
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

    baslangic = TURKIYE.localize(datetime.strptime(veri[kullanici_id]["baslangic"], "%Y-%m-%d %H:%M:%S"))
    simdi = tr_saat()
    saniye = (simdi - baslangic).total_seconds()
    saat = int(saniye / 3600)
    dakika = int((saniye % 3600) / 60)
    kazanc = (saniye / 3600) * SAAT_UCRETI
    kalan_saat = TAM_MESAI_SAAT - (saniye / 3600)

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
    mesaj += f"Su an    : {simdi.strftime('%H:%M:%S')}\n"
    mesaj += f"Gecen    : {saat}s {dakika}d\n"
    mesaj += f"Kazanc   : {kazanc:.2f} TL\n"
    mesaj += kalan_mesaj
    await update.message.reply_text(mesaj)

async def rapor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    veri = veri_yukle()
    if not veri:
        await update.message.reply_text("Henuz kayitli mesai verisi yok.")
        return

    simdi = tr_saat()
    bugun = simdi.strftime("%Y-%m-%d")

    mesaj = "MESAI RAPORU\n"
    mesaj += f"Tarih: {simdi.strftime('%d.%m.%Y %H:%M')}\n"
    mesaj += "=" * 30 + "\n\n"

    bugun_veri_var = False

    for uid, bilgi in veri.items():
        isim = bilgi.get("isim", "Bilinmeyen")
        baslangic_str = bilgi.get("baslangic", "")
        aktif = bilgi.get("aktif", False)

        if aktif and baslangic_str.startswith(bugun):
            bugun_veri_var = True
            baslangic_dt = TURKIYE.localize(datetime.strptime(baslangic_str, "%Y-%m-%d %H:%M:%S"))
            gecen = simdi - baslangic_dt
            saat = int(gecen.total_seconds() / 3600)
            dakika = int((gecen.total_seconds() % 3600) / 60)
            mesaj += f"AKTIF - {isim}\n"
            mesaj += f"   Baslangic: {baslangic_str[11:16]}\n"
            mesaj += f"   Gecen sure: {saat}s {dakika}d\n\n"

    if not bugun_veri_var:
        mesaj += "Bugun aktif mesai yok.\n"

    await update.message.reply_text(mesaj)

async def haftalik_rapor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    simdi = tr_saat()
    bugun = simdi.date()

    tarihler = []
    for i in range(7):
        gun = bugun - timedelta(days=i)
        tarihler.append(gun.strftime("%Y-%m-%d"))

    baslangic_tarihi = tarihler[-1]
    bitis_tarihi = tarihler[0]

    mesaj = "HAFTALIK CALISMA RAPORU\n"
    mesaj += f"Tarih: {baslangic_tarihi[8:]}.{baslangic_tarihi[5:7]}.{baslangic_tarihi[:4]}"
    mesaj += f" - {bitis_tarihi[8:]}.{bitis_tarihi[5:7]}.{bitis_tarihi[:4]}\n"
    mesaj += "=" * 30 + "\n\n"

    try:
        kayitlar = list(gecmis_collection.find({
            "tarih": {"$in": tarihler}
        }).sort("tarih", 1))

        if not kayitlar:
            mesaj += "Son 7 gunde calisma kaydi bulunamadi.\n\n"
            mesaj += "Not: Haftalik rapor yeni sistem ile bugunden itibaren tutulmaktadir."
            await update.message.reply_text(mesaj)
            return

        kisiler = {}
        for kayit in kayitlar:
            uid = kayit['kullanici_id']
            if uid not in kisiler:
                kisiler[uid] = {
                    'isim': kayit['isim'],
                    'gunler': [],
                    'toplam_saniye': 0,
                    'toplam_ucret': 0
                }

            sure_saat = kayit.get('sure_saat', 0)
            ucret = kayit.get('ucret', 0)
            tarih = kayit.get('tarih', '')
            tam_saat = int(sure_saat)
            kalan_dakika = int((sure_saat - tam_saat) * 60)

            kisiler[uid]['gunler'].append({
                'tarih': tarih,
                'saat': tam_saat,
                'dakika': kalan_dakika,
                'ucret': ucret
            })
            kisiler[uid]['toplam_saniye'] += sure_saat * 3600
            kisiler[uid]['toplam_ucret'] += ucret

        for uid, bilgi in kisiler.items():
            toplam_saat = int(bilgi['toplam_saniye'] / 3600)
            toplam_dakika = int((bilgi['toplam_saniye'] % 3600) / 60)
            gun_sayisi = len(bilgi['gunler'])

            mesaj += f"👤 {bilgi['isim']}\n"
            mesaj += "-" * 25 + "\n"

            for gun in sorted(bilgi['gunler'], key=lambda x: x['tarih']):
                t = gun['tarih']
                tarih_fmt = f"{t[8:]}.{t[5:7]}.{t[:4]}"
                mesaj += f"📅 {tarih_fmt}: {gun['saat']}s {gun['dakika']}d - {gun['ucret']:.0f} TL\n"

            mesaj += f"⏱️ Toplam : {toplam_saat}s {toplam_dakika}d\n"
            mesaj += f"💰 Kazanc : {bilgi['toplam_ucret']:.2f} TL\n"
            mesaj += f"📆 Calisilan Gun: {gun_sayisi}/7\n\n"

        await update.message.reply_text(mesaj)

    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")
        print(f"Haftalik rapor hatasi: {e}")

async def yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = "KOMUTLAR\n"
    mesaj += "=" * 30 + "\n"
    mesaj += "/mesai   - Mesai baslat\n"
    mesaj += "/cikis   - Mesai bitir\n"
    mesaj += "/durum   - Anlik mesai durumu\n"
    mesaj += "/rapor   - Gunluk rapor\n"
    mesaj += "/haftalik - Haftalik rapor\n"
    mesaj += "/yardim  - Bu mesaji gosterir\n"
    mesaj += "=" * 30 + "\n"
    mesaj += f"8 saat = {TAM_MESAI_UCRET} TL\n"
    mesaj += f"Saat basi = {SAAT_UCRETI:.2f} TL"
    await update.message.reply_text(mesaj)

def main():
    threading.Thread(target=web_sunucu, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mesai", mesai_baslat))
    app.add_handler(CommandHandler("cikis", mesai_bitir))
    app.add_handler(CommandHandler("durum", durum))
    app.add_handler(CommandHandler("rapor", rapor))
    app.add_handler(CommandHandler("haftalik", haftalik_rapor))
    app.add_handler(CommandHandler("yardim", yardim))

    simdi = tr_saat()
    print("Bot calisiyor...")
    print(f"Turkiye Saati: {simdi.strftime('%d.%m.%Y %H:%M:%S')}")
    app.run_polling()

if __name__ == "__main__":
    main()
