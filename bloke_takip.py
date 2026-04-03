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
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bloke Bot Calisiyor')
    def log_message(self, format, *args):
        pass

def web_sunucu():
    port = int(os.getenv('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheck)
    print("🌐 Web sunucu basladi")
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
    mesaj = "💰 *Banka Bloke Takip Botu*\n\n"
    mesaj += "📋 Komutlar:\n"
    mesaj += "/ekle - Yeni bloke ekle\n"
    mesaj += "/liste - Tüm blokeleri göster\n"
    mesaj += "/sil - Bloke sil\n"
    mesaj += "/toplam - Toplam tutarı göster\n"
    mesaj += "/iptal - Devam eden işlemi iptal et"
    await update.message.reply_text(mesaj, parse_mode='Markdown')

async def ekle_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    mesaj = "📝 *Yeni Bloke Ekleme*\n\n"
    mesaj += "👤 Banka sahibinin adını yazın:\n\n"
    mesaj += "_İptal etmek için /iptal yazın_"
    await update.message.reply_text(mesaj, parse_mode='Markdown')
    return SAHIP

async def sahip_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sahip = update.message.text.strip()
    if not sahip:
        await update.message.reply_text("❌ Lütfen geçerli bir isim girin!")
        return SAHIP
    context.user_data['sahip'] = sahip
    await update.message.reply_text(f"✅ Sahip: *{sahip}*\n\n🏦 Şimdi banka adını yazın:", parse_mode='Markdown')
    return BANKA

async def banka_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    banka = update.message.text.strip()
    if not banka:
        await update.message.reply_text("❌ Lütfen geçerli bir banka adı girin!")
        return BANKA
    context.user_data['banka'] = banka
    await update.message.reply_text(f"✅ Banka: *{banka}*\n\n💵 Son olarak bloke tutarını yazın:\n_Örnek: 5000 veya 5000.50_", parse_mode='Markdown')
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
        mesaj = "✅ *Bloke Başarıyla Eklendi!*\n\n"
        mesaj += f"🆔 ID: {yeni_kayit['id']}\n"
        mesaj += f"👤 Sahip: {sahip}\n"
        mesaj += f"🏦 Banka: {banka}\n"
        mesaj += f"💰 Tutar: {tutar:,.2f} ₺\n"
        mesaj += f"📅 Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        mesaj += "_Yeni bloke eklemek için tekrar /ekle yazabilirsin_"
        await update.message.reply_text(mesaj, parse_mode='Markdown')
        context.user_data.clear()
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ *Geçersiz tutar!*\n\nLütfen sadece rakam girin.\nÖrnek: 5000 veya 5000.50", parse_mode='Markdown')
        return TUTAR

async def iptal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ İşlem iptal edildi.\n\nYeni ekleme için /ekle yazabilirsin.")
    return ConversationHandler.END

async def liste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    veri = veri_yukle()
    if not veri:
        await update.message.reply_text("📋 Henüz kayıtlı bloke bulunmuyor.\n\nYeni bloke eklemek için /ekle komutunu kullan.")
        return
    mesaj = "📋 *BLOKE LİSTESİ*\n"
    mesaj += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    toplam = 0
    for kayit in veri:
        mesaj += f"🆔 *ID: {kayit['id']}*\n"
        mesaj += f"👤 Sahip: {kayit['sahip']}\n"
        mesaj += f"🏦 Banka: {kayit['banka']}\n"
        mesaj += f"💰 Tutar: {kayit['tutar']:,.2f} ₺\n"
        mesaj += f"📅 {kayit['tarih'][:10]}\n"
        mesaj += "─────────────────────\n"
        toplam += kayit['tutar']
    mesaj += f"\n💎 *TOPLAM: {toplam:,.2f} ₺*"
    await update.message.reply_text(mesaj, parse_mode='Markdown')

async def toplam_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    veri = veri_yukle()
    if not veri:
        await update.message.reply_text("📊 Henüz kayıtlı bloke bulunmuyor.")
        return
    toplam_tutar = sum(kayit['tutar'] for kayit in veri)
    kayit_sayisi = len(veri)
    bankalar = {}
    for kayit in veri:
        banka = kayit['banka']
        bankalar[banka] = bankalar.get(banka, 0) + kayit['tutar']
    sahipler = {}
    for kayit in veri:
        sahip = kayit['sahip']
        sahipler[sahip] = sahipler.get(sahip, 0) + kayit['tutar']
    mesaj = "📊 *BLOKE ÖZET RAPORU*\n"
    mesaj += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    mesaj += f"📌 Toplam Kayıt: {kayit_sayisi}\n"
    mesaj += f"💎 Toplam Tutar: *{toplam_tutar:,.2f} ₺*\n\n"
    if bankalar:
        mesaj += "🏦 *Banka Bazında:*\n"
        for banka, tutar in sorted(bankalar.items(), key=lambda x: x[1], reverse=True):
            yuzde = (tutar / toplam_tutar) * 100
            mesaj += f"  • {banka}: {tutar:,.2f} ₺ ({yuzde:.0f}%)\n"
    if sahipler:
        mesaj += "\n👥 *Sahip Bazında:*\n"
        for sahip, tutar in sorted(sahipler.items(), key=lambda x: x[1], reverse=True):
            yuzde = (tutar / toplam_tutar) * 100
            mesaj += f"  • {sahip}: {tutar:,.2f} ₺ ({yuzde:.0f}%)\n"
    await update.message.reply_text(mesaj, parse_mode='Markdown')

async def sil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    veri = veri_yukle()
    if not veri:
        await update.message.reply_text("❌ Silinecek bloke bulunmuyor.")
        return
    keyboard = []
    for kayit in veri:
        buton_text = f"ID:{kayit['id']} | {kayit['sahip']} - {kayit['banka']} ({kayit['tutar']:,.0f}₺)"
        keyboard.append([InlineKeyboardButton(buton_text, callback_data=f"sil_{kayit['id']}")])
    keyboard.append([InlineKeyboardButton("❌ İptal", callback_data="sil_iptal")])
    await update.message.reply_text("🗑️ *Silmek istediğin blokeyi seç:*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def sil_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "sil_iptal":
        await query.edit_message_text("❌ Silme işlemi iptal edildi.")
        return
    kayit_id = int(query.data.split('_')[1])
    veri = veri_yukle()
    silinen = None
    yeni_veri = [k for k in veri if k['id'] != kayit_id]
    for k in veri:
        if k['id'] == kayit_id:
            silinen = k
            break
    if silinen and len(yeni_veri) < len(veri):
        veri_kaydet(yeni_veri)
        mesaj = "✅ *Bloke Silindi!*\n\n"
        mesaj += f"🆔 ID: {silinen['id']}\n"
        mesaj += f"👤 Sahip: {silinen['sahip']}\n"
        mesaj += f"🏦 Banka: {silinen['banka']}\n"
        mesaj += f"💰 Tutar: {silinen['tutar']:,.2f} ₺"
        await query.edit_message_text(mesaj, parse_mode='Markdown')
    else:
        await query.edit_message_text("❌ Kayıt bulunamadı!")

async def yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = "📖 *YARDIM - KOMUTLAR*\n"
    mesaj += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    mesaj += "➕ */ekle* - Yeni bloke ekle\n"
    mesaj += "📋 */liste* - Tüm blokeleri listele\n"
    mesaj += "🗑️ */sil* - Bloke sil\n"
    mesaj += "📊 */toplam* - Özet rapor\n"
    mesaj += "❓ */yardim* - Bu mesajı gösterir"
    await update.message.reply_text(mesaj, parse_mode='Markdown')

def main():
    threading.Thread(target=web_sunucu, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    ekle_handler = ConversationHandler(
        entry_points=[CommandHandler('ekle', ekle_baslat)],
        states={
            SAHIP: [MessageHandler(filters.TEXT & ~filters.COMMAND, sahip_al)],
            BANKA: [MessageHandler(filters.TEXT & ~filters.COMMAND, banka_al)],
            TUTAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutar_al)],
        },
        fallbacks=[CommandHandler('iptal', iptal)],
        allow_reentry=True,
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ekle_handler)
    app.add_handler(CommandHandler("liste", liste))
    app.add_handler(CommandHandler("toplam", toplam_cmd))
    app.add_handler(CommandHandler("sil", sil))
    app.add_handler(CommandHandler("yardim", yardim))
    app.add_handler(CallbackQueryHandler(sil_callback, pattern="^sil_"))
    print("💰 Bloke Takip Botu çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
