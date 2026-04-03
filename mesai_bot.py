import json
import os
from datetime import datetime, timedelta
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ===================== AYARLAR =====================
BOT_TOKEN = "8644328245:AAE-WcsSJ0-BHG9KaReQfh2FR4Cp8dIlLcM"
SAAT_UCRETI = 2000 / 8  # 8 saat = 2000₺, saat başı 250₺
TAM_MESAI_SAAT = 8
TAM_MESAI_UCRET = 2000
VERI_DOSYASI = "mesai_verileri.json"
TURKIYE = pytz.timezone('Europe/Istanbul')
UTC = pytz.UTC
# ===================================================

def tr_saat():
    """Türkiye saatini döndür"""
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
    
    # Başlangıç saatini al
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

async def durum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kullanici = update.effective_user
    kullanici_id = str(kullanici.id)
    kullanici_adi = kullanici.first_name or kullanici.username or "Bilinmeyen"
    veri = veri_yukle()
    
    if kullanici_id not in veri or not veri[kullanici_id].get("aktif"):
        await update.message.reply_text(f"ℹ️ {kullanici_adi}, şu an mesaide değilsin.")
        return
    
    baslangic_str = veri[kullanici_id]["baslangic"]
    baslangic = datetime.strptime(baslangic_str, "%Y-%m-%d %H:%M:%S")
    baslangic = TURKIYE.localize(baslangic)
    
    simdi = tr_saat()
    fark = simdi - baslangic
    toplam_saniye = fark.total_seconds()
    saat = int(toplam_saniye / 3600)
    dakika = int((toplam_saniye % 3600) / 60)
    
    anlık_kazanc = (toplam_saniye / 3600) * SAAT_UCRETI
    kalan_saat = TAM_MESAI_SAAT - (toplam_saniye / 3600)
    
    if kalan_saat > 0:
        kalan_s = int(kalan_saat)
        kalan_d = int((kalan_saat - kalan_s) * 60)
        kalan_mesaj = f"⏳ Tam mesaiye kalan: {kalan_s} saat {kalan_d} dakika"
    else:
        kalan_mesaj = "🎉 Tam mesaiyi tamamladın!"
    
    await update.message.reply_text(
        f"📊 {kullanici_adi} - Mesai Durumu\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🟢 Mesaide\n"
        f"🕐 Başlangıç: {baslangic.strftime('%H:%M:%S')}\n"
        f"🕐 Şu an: {simdi.strftime('%H:%M:%S')}\n"
        f"⏱️ Geçen süre: {saat}s {dakika}d\n"
        f"💰 Anlık kazanç: {anlık_kazanc:.2f}₺\n"
        f"{kalan_mesaj}"
    )

async def rapor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    veri = veri_yukle()
    if not veri:
        await update.message.reply_text("📋 Henüz kayıtlı mesai verisi yok.")
        return
    
    simdi = tr_saat()
    mesaj = f"📋 MESAI RAPORU\n"
    mesaj += f"🕐 Rapor Saati: {simdi.strftime('%d.%m.%Y %H:%M:%S')}\n"
    mesaj += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for uid, bilgi in veri.items():
        isim = bilgi.get("isim", "Bilinmeyen")
        durum_emoji = "🟢" if bilgi.get("aktif") else "🔴"
        durum_text = "Mesaide" if bilgi.get("aktif") else "Mesaide değil"
        toplam = bilgi.get("toplam_kazanc", 0)
        
        mesaj += f"{durum_emoji} {isim}: {durum_text}\n"
        
        if bilgi.get("aktif"):
            baslangic_str = bilgi.get("baslangic", "")
            if baslangic_str:
                mesaj += f"   🕐 Başlangıç: {baslangic_str[11:19]}\n"
        
        mesaj += f"   💰 Toplam kazanç: {toplam:.2f}₺\n\n"
    
    await update.message.reply_text(mesaj)

async def yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 KOMUTLAR\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "/mesai  → Mesaini başlat\n"
        "/cikis  → Mesaini bitir\n"
        "/durum  → Anlık mesai durumu\n"
        "/rapor  → Tüm çalışanların raporu\n"
        "/yardim → Bu mesajı gösterir\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 8 saat = {TAM_MESAI_UCRET}₺ | Saat başı = {SAAT_UCRETI:.2f}₺"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    simdi = tr_saat()
    await update.message.reply_text(
        f"👋 Merhaba! Mesai Takip Botuna hoş geldin!\n\n"
        f"🕐 Şu anki Türkiye saati: {simdi.strftime('%d.%m.%Y %H:%M:%S')}\n\n"
        f"Mesaini başlatmak için /mesai yaz.\n"
        f"Tüm komutlar için /yardim yaz."
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mesai", mesai_baslat))
    app.add_handler(CommandHandler("cikis", mesai_bitir))
    app.add_handler(CommandHandler("durum", durum))
    app.add_handler(CommandHandler("rapor", rapor))
    app.add_handler(CommandHandler("yardim", yardim))
    
    simdi = tr_saat()
    print(f"🤖 Bot çalışıyor...")
    print(f"🕐 Türkiye Saati: {simdi.strftime('%d.%m.%Y %H:%M:%S')}")
    app.run_polling()

if __name__ == "__main__":
    main()