import os
import sys
from dotenv import load_dotenv
load_dotenv()

import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import httpx

API_URL = os.getenv("API_URL", "http://localhost:8000")
token = os.getenv("TELEGRAM_BOT_TOKEN")
print(f"DEBUG: API_URL={API_URL}", flush=True)
print(f"DEBUG: TOKEN={'SET (' + token[:10] + '...)' if token else 'NOT SET'}", flush=True)
print(f"DEBUG: All env vars with TELEGRAM: {[k for k in os.environ if 'TELEGRAM' in k.upper()]}", flush=True)

# Store user chat_id for notifications
USER_CHAT_ID = None


async def get_json(path: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_URL}{path}")
        r.raise_for_status()
        return r.json()


async def post_json(path: str, data: dict):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{API_URL}{path}", json=data)
        r.raise_for_status()
        return r.json()


async def put_json(path: str, data: dict):
    async with httpx.AsyncClient() as client:
        r = await client.put(f"{API_URL}{path}", json=data)
        r.raise_for_status()
        return r.json()


# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USER_CHAT_ID
    USER_CHAT_ID = update.effective_chat.id
    await update.message.reply_text(
        "💳 *CreditoSubaru Bot*\n\n"
        "Comandos:\n"
        "/bancos - Ver tus bancos\n"
        "/gasto - Registrar gasto en tarjeta\n"
        "/resumen - Resumen de uso de credito\n"
        "/ayuda - Ver ayuda",
        parse_mode="Markdown",
    )


# /bancos
async def bancos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    banks = await get_json("/api/banks")
    if not banks:
        await update.message.reply_text("No hay bancos registrados.")
        return

    text = "*Tus Bancos:*\n\n"
    for b in banks:
        data = await get_json(f"/api/banks/{b['id']}/data")
        accounts = data.get("accounts", [])
        cards = data.get("credit_cards", [])

        text += f"*{b['name']}*\n"
        for a in accounts:
            bal = f"${a['balance']:,.0f}"
            text += f"  💰 {a['name']}: {bal}\n"
        for c in cards:
            used = c["used_credit"]
            limit = c["credit_limit"]
            pct = (used / limit * 100) if limit > 0 else 0
            available = limit - used
            text += f"  💳 {c['name']}\n"
            text += f"     Usado: ${used:,.0f} / ${limit:,.0f} ({pct:.1f}%)\n"
            text += f"     Disponible: ${available:,.0f}\n"
        text += "\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# /gasto
async def gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    banks = await get_json("/api/banks")
    if not banks:
        await update.message.reply_text("No hay bancos registrados.")
        return

    # Build cards list
    all_cards = []
    for b in banks:
        data = await get_json(f"/api/banks/{b['id']}/data")
        for c in data.get("credit_cards", []):
            all_cards.append({
                "bank_name": b["name"],
                "bank_id": b["id"],
                "card_id": c["id"],
                "card_name": c["name"],
                "credit_limit": c["credit_limit"],
                "used_credit": c["used_credit"],
            })

    if not all_cards:
        await update.message.reply_text("No hay tarjetas de credito registradas.")
        return

    context.user_data["cards"] = all_cards

    keyboard = []
    for i, c in enumerate(all_cards):
        keyboard.append([
            InlineKeyboardButton(
                f"{c['bank_name']} - {c['card_name']}",
                callback_data=f"card_{i}",
            )
        ])

    await update.message.reply_text(
        "*Selecciona la tarjeta:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def card_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx = int(query.data.split("_")[1])
    card = context.user_data["cards"][idx]
    context.user_data["selected_card"] = card

    used = card["used_credit"]
    limit = card["credit_limit"]
    pct = (used / limit * 100) if limit > 0 else 0
    available = limit - used

    text = (
        f"*{card['bank_name']} - {card['card_name']}*\n\n"
        f"Credito total: ${limit:,.0f}\n"
        f"Usado: ${used:,.0f} ({pct:.1f}%)\n"
        f"Disponible: ${available:,.0f}\n\n"
        f"Meta: usar max 30% (${limit * 0.3:,.0f})\n"
    )

    if pct >= 30:
        text += "⚠️ *ALERTA: Ya superaste el 30%!*\n"
    elif pct >= 20:
        text += "🟡 *Estas en el rango ideal (20-30%)*\n"
    else:
        text += "✅ *Vas bien, bajo el 20%*\n"

    await query.edit_message_text(text, parse_mode="Markdown")

    await query.message.reply_text(
        "Escribe el monto del gasto (solo numeros):",
    )
    context.user_data["awaiting_amount"] = True


async def amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_amount"):
        return

    try:
        amount = float(update.message.text.replace(".", "").replace(",", ""))
    except ValueError:
        await update.message.reply_text("Monto invalido. Escribe solo numeros.")
        return

    context.user_data["awaiting_amount"] = False
    card = context.user_data["selected_card"]

    # Register the expense
    await post_json("/api/transactions", {
        "bank_id": card["bank_id"],
        "credit_card_id": card["card_id"],
        "type": "gasto",
        "amount": amount,
        "merchant": "Gasto manual",
        "category": "Manual",
        "description": f"Gasto registrado via Telegram",
    })

    # Get updated card data
    updated_cards = await get_json(f"/api/banks/{card['bank_id']}/data")
    for c in updated_cards.get("credit_cards", []):
        if c["id"] == card["card_id"]:
            new_used = c["used_credit"]
            limit = c["credit_limit"]
            break

    new_pct = (new_used / limit * 100) if limit > 0 else 0
    available = limit - new_used
    target_30 = limit * 0.3

    text = (
        f"*Gasto registrado: ${amount:,.0f}*\n\n"
        f"*{card['bank_name']} - {card['card_name']}*\n"
        f"Usado: ${new_used:,.0f} / ${limit:,.0f} ({new_pct:.1f}%)\n"
        f"Disponible: ${available:,.0f}\n\n"
    )

    if new_pct >= 30:
        text += "🔴 *ALERTA: Superaste el 30%!*\n"
        text += "No uses mas esta tarjeta hasta pagar.\n"
    elif new_pct >= 20:
        text += f"🟡 *En rango ideal (20-30%)*\n"
        remaining = target_30 - new_used
        if remaining > 0:
            text += f"Puedes usar ${remaining:,.0f} mas antes del limite.\n"
    else:
        text += f"✅ *Vas bien* - Puedes usar ${target_30 - new_used:,.0f} mas.\n"

    # Suggest Mercado Pago transfer
    text += (
        f"\n💡 *Sugerencia:*\n"
        f"¿Depositar ${amount:,.0f} en Mercado Pago para\n"
        f"resguardarlo y ganar intereses hasta pagar la tarjeta?\n"
        f"Tasa actual: 5% anual.\n"
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Si, transferir a MP", callback_data=f"transfer_{card['card_id']}_{amount}"),
            InlineKeyboardButton("❌ No, dejar asi", callback_data="cancel_transfer"),
        ]
    ]

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def transfer_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    card_id = parts[1]
    amount = float(parts[2])

    # Find Mercado Pago account
    banks = await get_json("/api/banks")
    mp_account = None
    mp_bank_id = None
    for b in banks:
        if b["name"] == "Mercado Pago":
            data = await get_json(f"/api/banks/{b['id']}/data")
            for a in data.get("accounts", []):
                mp_account = a
                mp_bank_id = b["id"]
                break

    if not mp_account:
        await query.edit_message_text("❌ No se encontro cuenta de Mercado Pago.")
        return

    # Create transfer transaction (gasto from MP)
    await post_json("/api/transactions", {
        "bank_id": mp_bank_id,
        "account_id": mp_account["id"],
        "type": "gasto",
        "amount": amount,
        "merchant": "Transferencia a MP",
        "category": "Resguardo",
        "description": f"Resguardo de gasto en tarjeta - ${amount:,.0f}",
    })

    new_balance = mp_account["balance"] - amount

    await query.edit_message_text(
        f"*Transferencia registrada*\n\n"
        f"Se descontaron ${amount:,.0f} de Ahorro MP.\n"
        f"Saldo actual: ${new_balance:,.0f}\n\n"
        f"💡 El dinero estara generando intereses (5% anual)\n"
        f"hasta que pagues la tarjeta.",
        parse_mode="Markdown",
    )


async def transfer_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Ok, no se realiza transferencia.")


# /resumen
async def resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    banks = await get_json("/api/banks")
    text = "*RESUMEN DE CREDITO*\n\n"
    total_used = 0
    total_limit = 0

    for b in banks:
        data = await get_json(f"/api/banks/{b['id']}/data")
        for c in data.get("credit_cards", []):
            used = c["used_credit"]
            limit = c["credit_limit"]
            pct = (used / limit * 100) if limit > 0 else 0
            total_used += used
            total_limit += limit

            status = "✅" if pct < 20 else "🟡" if pct < 30 else "🔴"
            text += f"{status} *{b['name']}* - {c['name']}\n"
            text += f"   ${used:,.0f} / ${limit:,.0f} ({pct:.1f}%)\n\n"

    if total_limit > 0:
        total_pct = (total_used / total_limit * 100)
        text += (
            f"*TOTAL:* ${total_used:,.0f} / ${total_limit:,.0f} ({total_pct:.1f}%)\n"
        )
        if total_pct >= 30:
            text += "🔴 *ALERTA: Superaste el 30% global!*"
        elif total_pct >= 20:
            text += "🟡 *En rango ideal*"
        else:
            text += "✅ *Todo bien*"

    await update.message.reply_text(text, parse_mode="Markdown")


# /ayuda
async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Ayuda - CreditoSubaru Bot*\n\n"
        "/bancos - Ver todas tus cuentas y tarjetas\n"
        "/gasto - Registrar un gasto en tarjeta de credito\n"
        "/resumen - Ver resumen de uso de credito\n\n"
        "*Objetivo:* Usar entre 20-30% del credito\n"
        "para mejorar tu historial crediticio.",
        parse_mode="Markdown",
    )


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("ERROR: Define TELEGRAM_BOT_TOKEN")
        return

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bancos", bancos))
    app.add_handler(CommandHandler("gasto", gasto))
    app.add_handler(CommandHandler("resumen", resumen))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(CallbackQueryHandler(card_selected, pattern=r"^card_"))
    app.add_handler(CallbackQueryHandler(transfer_yes, pattern=r"^transfer_"))
    app.add_handler(CallbackQueryHandler(transfer_no, pattern=r"^cancel_transfer"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, amount_received))

    print("Bot started!")
    app.run_polling()


if __name__ == "__main__":
    main()
