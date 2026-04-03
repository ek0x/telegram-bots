import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters

# ===================== AYARLAR =====================
BOT_TOKEN = "8638044446:AAFKqrfmvgIfUaqZM0Rxse8NW4Vr-OBpFTE"
VERI_DOSYASI = "bloke_verileri.json"
# ===================================================

# Conversation states
SAHIP, BANKA, TUTAR = range(3)

# ---------- Veri İşlemleri ----------
def veri_yukle():
    if os.path.exists(VERI_DOSYASI):
        with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def veri_kaydet(veri):
    with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)

# ---------- /start ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💰 *Banka Bloke Takip Botuna Hoş Geldin!*\n\n"
        "📋 *Komutlar:*\n"
        "/ekle - Yeni bloke ekle\n"
        "/liste - Tüm blokeleri göster\n"
        "/sil - Bloke sil\n"
        "/toplam - Toplam bloke tutarını göster\n"
        "/yardim - Yardım mesajı\n",
        parse_mode='Markdown'
    )

# ---------- /ekle Başlat ----------
async def ekle_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 *Yeni Bloke Ekleme*\n\n"
        "👤 Banka sahibinin adını yazın:\n"
        "(İptal için /iptal yazın)",
        parse_mode='Markdown'
    )
    return SAHIP

async def sahip_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['sahip'] = update.message.text
    await update.message.reply_text(
        f"✅ Sahip: *{update.message.text}*\n\n"
        f"🏦 Banka adını yazın:",
        parse_mode='Markdown'
    )
    return BANKA

async def banka_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['banka'] = update.message.text
    await update.message.reply_text(
        f"✅ Banka: *{update.message.text}*\n\n"
        f"💵 Bloke tutarını yazın (sadece rakam):\n"
        f"Örnek: 5000",
        parse_mode='Markdown'
    )
    return TUTAR

async def tutar_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tutar = float(update.message.text.replace(',', '.'))
        
        sahip = context.user_data['sahip']
        banka = context.user_data['banka']
        
        veri = veri_yukle()
        yeni_kayit = {
            "id": len(veri) + 1,
            "sahip": sahip,
            "banka": banka,
            "tutar": tutar,
            "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ekleyen": update.effective_user.first_name or update.effective_user.username or "Bilinmeyen"
        }
        
        veri.append(yeni_kayit)
        veri_kaydet(veri)
        
        await update.message.reply_text(
            f"✅ *Bloke Başarıyla Eklendi!*\n\n"
            f"👤 Sahip: {sahip}\n"
            f"🏦 Banka: {banka}\n"
            f"💰 Tutar: {tutar:,.2f} ₺\n"
            f"📅 Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            f"➕ Ekleyen: {yeni_kayit['ekleyen']}",
            parse_mode='Markdown'
        )
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(
            "❌ Lütfen geçerli bir sayı girin!\n"
            "Örnek: 5000 veya 5000.50"
        )
        return TUTAR

async def iptal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ İşlem iptal edildi.")
    return ConversationHandler.END

# ---------- /liste ----------
async def liste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    veri = veri_yukle()
    
    if not veri:
        await update.message.reply_text(
            "📋 Henüz kayıtlı bloke bulunmuyor.\n\n"
            "Yeni bloke eklemek için /ekle komutunu kullan."
        )
        return
    
    mesaj = "📋 *BLOKE LİSTESİ*\n"
    mesaj += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    toplam = 0
    for kayit in veri:
        mesaj += f"🆔 ID: {kayit['id']}\n"
        mesaj += f"👤 Sahip: {kayit['sahip']}\n"
        mesaj += f"🏦 Banka: {kayit['banka']}\n"
        mesaj += f"💰 Tutar: {kayit['tutar']:,.2f} ₺\n"
        mesaj += f"📅 Tarih: {kayit['tarih'][:10]}\n"
        mesaj += "─────────────────────\n"
        toplam += kayit['tutar']
    
    mesaj += f"\n💎 *TOPLAM: {toplam:,.2f} ₺*"
    
    await update.message.reply_text(mesaj, parse_mode='Markdown')

# ---------- /toplam ----------
async def toplam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    veri = veri_yukle()
    
    if not veri:
        await update.message.reply_text("📊 Henüz kayıtlı bloke bulunmuyor.")
        return
    
    toplam_tutar = sum(kayit['tutar'] for kayit in veri)
    kayit_sayisi = len(veri)
    
    # Banka bazında grupla
    bankalar = {}
    for kayit in veri:
        banka = kayit['banka']
        if banka not in bankalar:
            bankalar[banka] = 0
        bankalar[banka] += kayit['tutar']
    
    # Sahip bazında grupla
    sahipler = {}
    for kayit in veri:
        sahip = kayit['sahip']
        if sahip not in sahipler:
            sahipler[sahip] = 0
        sahipler[sahip] += kayit['tutar']
    
    mesaj = "📊 *BLOKE ÖZET RAPORU*\n"
    mesaj += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    mesaj += f"📌 Toplam Kayıt: {kayit_sayisi}\n"
    mesaj += f"💎 Toplam Tutar: *{toplam_tutar:,.2f} ₺*\n\n"
    
    mesaj += "🏦 *Banka Bazında:*\n"
    for banka, tutar in sorted(bankalar.items(), key=lambda x: x[1], reverse=True):
        yuzde = (tutar / toplam_tutar) * 100
        mesaj += f"  • {banka}: {tutar:,.2f} ₺ ({yuzde:.1f}%)\n"
    
    mesaj += "\n👥 *Sahip Bazında:*\n"
    for sahip, tutar in sorted(sahipler.items(), key=lambda x: x[1], reverse=True):
        yuzde = (tutar / toplam_tutar) * 100
        mesaj += f"  • {sahip}: {tutar:,.2f} ₺ ({yuzde:.1f}%)\n"
    
    await update.message.reply_text(mesaj, parse_mode='Markdown')

# ---------- /sil ----------
async def sil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    veri = veri_yukle()
    
    if not veri:
        await update.message.reply_text("❌ Silinecek bloke bulunmuyor.")
        return
    
    keyboard = []
    for kayit in veri:
        buton_text = f"🆔 {kayit['id']} | {kayit['sahip']} - {kayit['banka']} ({kayit['tutar']:,.0f} ₺)"
        keyboard.append([InlineKeyboardButton(buton_text, callback_data=f"sil_{kayit['id']}")])
    
    keyboard.append([InlineKeyboardButton("❌ İptal", callback_data="sil_iptal")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🗑️ *Silmek istediğin blokeyi seç:*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def sil_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "sil_iptal":
        await query.edit_message_text("❌ Silme işlemi iptal edildi.")
        return
    
    kayit_id = int(query.data.split('_')[1])
    veri = veri_yukle()
    
    silinen = None
    yeni_veri = []
    for kayit in veri:
        if kayit['id'] == kayit_id:
            silinen = kayit
        else:
            yeni_veri.append(kayit)
    
    if silinen:
        veri_kaydet(yeni_veri)
        await query.edit_message_text(
            f"✅ *Bloke Silindi!*\n\n"
            f"👤 Sahip: {silinen['sahip']}\n"
            f"🏦 Banka: {silinen['banka']}\n"
            f"💰 Tutar: {silinen['tutar']:,.2f} ₺",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text("❌ Kayıt bulunamadı!")

# ---------- /yardim ----------
async def yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *YARDIM - KOMUTLAR*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "➕ */ekle* - Yeni bloke ekle\n"
        "   Sahip, banka ve tutar bilgilerini adım adım gir\n\n"
        "📋 */liste* - Tüm blokeleri listele\n"
        "   Tüm kayıtlı blokeleri detaylı gösterir\n\n"
        "🗑️ */sil* - Bloke sil\n"
        "   Listeden seçerek bloke silebilirsin\n\n"
        "📊 */toplam* - Özet rapor\n"
        "   Toplam tutar, banka ve sahip bazında dağılım\n\n"
        "❓ */yardim* - Bu mesajı gösterir\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *İpucu:* Tutarları virgül veya nokta ile yazabilirsin\n"
        "Örnek: 5000 veya 5000.50",
        parse_mode='Markdown'
    )

# ---------- Ana Program ----------
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Conversation handler for /ekle
    ekle_handler = ConversationHandler(
        entry_points=[CommandHandler('ekle', ekle_baslat)],
        states={
            SAHIP: [MessageHandler(filters.TEXT & ~filters.COMMAND, sahip_al)],
            BANKA: [MessageHandler(filters.TEXT & ~filters.COMMAND, banka_al)],
            TUTAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutar_al)],
        },
        fallbacks=[CommandHandler('iptal', iptal)],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ekle_handler)
    app.add_handler(CommandHandler("liste", liste))
    app.add_handler(CommandHandler("toplam", toplam))
    app.add_handler(CommandHandler("sil", sil))
    app.add_handler(CommandHandler("yardim", yardim))
    app.add_handler(CallbackQueryHandler(sil_callback, pattern="^sil_"))
    
    print("💰 Bloke Takip Botu çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()