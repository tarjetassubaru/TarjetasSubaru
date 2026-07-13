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


async def api_get(path: str):
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{API_URL}{path}")
        r.raise_for_status()
        return r.json()


async def api_post(path: str, data: dict):
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{API_URL}{path}", json=data)
        r.raise_for_status()
        return r.json()


def fmt_money(amount: float) -> str:
    return f"${amount:,.0f}".replace(",", ".")


def credit_pct(used: float, limit: float) -> float:
    return (used / limit * 100) if limit > 0 else 0


def credit_emoji(pct: float) -> str:
    if pct >= 30:
        return "🔴"
    elif pct >= 20:
        return "🟡"
    return "🟢"


def credit_status(pct: float) -> str:
    if pct >= 30:
        return "ALERTA: Superaste el 30%"
    elif pct >= 20:
        return "En rango ideal (20-30%)"
    return "Vas bien, bajo el 20%"


# ─── /start ───
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("🏦 Ver Bancos", callback_data="menu_banks")],
        [InlineKeyboardButton("📊 Mi Resumen", callback_data="menu_summary")],
        [InlineKeyboardButton("💸 Transferir", callback_data="menu_transfer")],
        [InlineKeyboardButton("❓ Ayuda", callback_data="menu_help")],
    ]
    await update.message.reply_text(
        "*CreditoSubaru*\nQue quieres hacer?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# ─── MAIN MENU CALLBACKS ───
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_banks":
        await show_banks_list(query, context)
    elif data == "menu_summary":
        await show_summary(query, context)
    elif data == "menu_transfer":
        await start_transfer(query, context, all_accounts=True)
    elif data == "menu_help":
        await show_help(query)
    elif data == "menu_main":
        await show_main_menu(query)
    elif data.startswith("bank_"):
        await show_bank_detail(query, context, data)
    elif data.startswith("action_"):
        await handle_bank_action(query, context, data)


async def show_main_menu(query):
    keyboard = [
        [InlineKeyboardButton("🏦 Ver Bancos", callback_data="menu_banks")],
        [InlineKeyboardButton("📊 Mi Resumen", callback_data="menu_summary")],
        [InlineKeyboardButton("💸 Transferir", callback_data="menu_transfer")],
        [InlineKeyboardButton("❓ Ayuda", callback_data="menu_help")],
    ]
    await query.edit_message_text(
        "*CreditoSubaru*\nQue quieres hacer?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# ─── BANKS LIST ───
async def show_banks_list(query, context):
    banks = await api_get("/api/banks")
    if not banks:
        await query.edit_message_text("No hay bancos registrados.")
        return

    context.user_data["banks"] = {b["id"]: b for b in banks}
    keyboard = []
    for b in banks:
        keyboard.append([InlineKeyboardButton(b["name"], callback_data=f"bank_{b['id']}")])
    keyboard.append([InlineKeyboardButton("◀️ Volver", callback_data="menu_main")])

    await query.edit_message_text(
        "*Selecciona un banco:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# ─── BANK DETAIL ───
async def show_bank_detail(query, context, data):
    try:
        bank_id = data.replace("bank_", "")
        bank = context.user_data.get("banks", {}).get(bank_id)
        if not bank:
            banks = await api_get("/api/banks")
            context.user_data["banks"] = {b["id"]: b for b in banks}
            bank = context.user_data["banks"].get(bank_id)

        if not bank:
            await query.edit_message_text("Banco no encontrado. Intenta con /start")
            return

        bd = await api_get(f"/api/banks/{bank_id}/data")
        accounts = bd.get("accounts", [])
        cards = bd.get("credit_cards", [])

        text = f"*{bank['name']}*\n\n"
        if accounts:
            text += "Cuentas:\n"
            for a in accounts:
                text += f"  💰 {a['name']}: {fmt_money(a['balance'])}\n"
        if cards:
            text += "\nTarjetas:\n"
            for c in cards:
                pct = credit_pct(c["used_credit"], c["credit_limit"])
                text += f"  💳 {c['name']}: {fmt_money(c['used_credit'])} / {fmt_money(c['credit_limit'])} ({pct:.0f}%)\n"

        context.user_data["current_bank_id"] = bank_id
        keyboard = [
            [InlineKeyboardButton("🛒 Gasto Tarjeta", callback_data=f"action_expense_{bank_id}")],
            [InlineKeyboardButton("📜 Historial", callback_data=f"action_history_{bank_id}")],
            [InlineKeyboardButton("💸 Transferir", callback_data=f"action_transfer_{bank_id}")],
            [InlineKeyboardButton("💳 Pagar Tarjeta", callback_data=f"action_pay_{bank_id}")],
            [InlineKeyboardButton("📥 Registrar Ingreso", callback_data=f"action_income_{bank_id}")],
            [InlineKeyboardButton("◀️ Volver", callback_data="menu_banks")],
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
    except Exception as e:
        print(f"ERROR in show_bank_detail: {e}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        try:
            await query.edit_message_text("Error al cargar banco. Intenta con /start")
        except Exception:
            pass


# ─── BANK ACTIONS ───
async def handle_bank_action(query, context, data):
    try:
        parts = data.split("_", 2)
        action = parts[1]
        bank_id = parts[2] if len(parts) > 2 else context.user_data.get("current_bank_id")

        if action == "history":
            await show_history(query, context, bank_id)
        elif action == "expense":
            await start_expense(query, context, bank_id)
        elif action == "transfer":
            await start_transfer_from_bank(query, context, bank_id)
        elif action == "pay":
            await start_pay_card(query, context, bank_id)
        elif action == "income":
            await start_income(query, context, bank_id)
    except Exception as e:
        print(f"ERROR in handle_bank_action: {e}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        try:
            await query.edit_message_text("Error. Intenta con /start")
        except Exception:
            pass


# ─── HISTORY ───
async def show_history(query, context, bank_id):
    txns = await api_get(f"/api/transactions?bank_id={bank_id}&limit=10")
    bank = context.user_data.get("banks", {}).get(bank_id, {"name": "Banco"})

    if not txns:
        await query.edit_message_text(
            f"*{bank['name']}*\nNo hay movimientos recientes.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Volver", callback_data=f"bank_{bank_id}")]
            ]),
            parse_mode="Markdown",
        )
        return

    text = f"*{bank['name']} - Ultimos movimientos*\n\n"
    for t in txns:
        icon = "📤" if t["type"] == "gasto" else "📥"
        date = t["created_at"][:10]
        merchant = t.get("merchant") or t.get("category") or "Movimiento"
        text += f"{icon} {fmt_money(t['amount'])} - {merchant} - {date}\n"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Volver", callback_data=f"bank_{bank_id}")]
        ]),
        parse_mode="Markdown",
    )


# ─── TRANSFER ───
async def start_transfer(query, context, all_accounts=False):
    accounts = await api_get("/api/accounts/all")
    if not accounts:
        await query.edit_message_text("No hay cuentas disponibles.")
        return

    context.user_data["all_accounts"] = {a["id"]: a for a in accounts}
    keyboard = []
    for a in accounts:
        banks = context.user_data.get("banks", {})
        bank_name = ""
        for b in context.user_data.get("banks", {}).values():
            if b["id"] == a["bank_id"]:
                bank_name = b["name"]
                break
        if not bank_name:
            bank_name = "Banco"
        keyboard.append([
            InlineKeyboardButton(
                f"{bank_name} - {a['name']}: {fmt_money(a['balance'])}",
                callback_data=f"tsrc_{a['id']}",
            )
        ])
    keyboard.append([InlineKeyboardButton("◀️ Cancelar", callback_data="menu_main")])

    await query.edit_message_text(
        "*Transferir*\nElige la cuenta de origen:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def start_transfer_from_bank(query, context, bank_id):
    await start_transfer(query, context)


async def transfer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("tsrc_"):
        src_id = data.replace("tsrc_", "")
        context.user_data["transfer_src"] = src_id
        accounts = context.user_data.get("all_accounts", {})
        keyboard = []
        for aid, a in accounts.items():
            if aid == src_id:
                continue
            banks = context.user_data.get("banks", {})
            bank_name = "Banco"
            for b in banks.values():
                if b["id"] == a["bank_id"]:
                    bank_name = b["name"]
                    break
            keyboard.append([
                InlineKeyboardButton(
                    f"{bank_name} - {a['name']}: {fmt_money(a['balance'])}",
                    callback_data=f"tdst_{aid}",
                )
            ])
        keyboard.append([InlineKeyboardButton("◀️ Cancelar", callback_data="menu_main")])

        await query.edit_message_text(
            "*Transferir*\nElige la cuenta de destino:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    elif data.startswith("tdst_"):
        dst_id = data.replace("tdst_", "")
        context.user_data["transfer_dst"] = dst_id
        await query.edit_message_text(
            "*Transferir*\nEscribe el monto (solo numeros):",
            parse_mode="Markdown",
        )
        context.user_data["awaiting_transfer_amount"] = True

    elif data == "confirm_transfer":
        await execute_transfer(query, context)

    elif data == "cancel_transfer":
        await show_main_menu(query)


async def execute_transfer(query, context):
    src_id = context.user_data.get("transfer_src")
    dst_id = context.user_data.get("transfer_dst")
    amount = context.user_data.get("transfer_amount")

    result = await api_post("/api/transfer", {
        "source_account_id": src_id,
        "destination_account_id": dst_id,
        "amount": amount,
        "description": "Transferencia via Telegram bot",
    })

    src = result["source"]
    dst = result["destination"]

    await query.edit_message_text(
        f"*Transferencia realizada*\n\n"
        f"📤 {src['name']}: {fmt_money(src['balance'])}\n"
        f"📥 {dst['name']}: {fmt_money(dst['balance'])}\n\n"
        f"Monto: {fmt_money(amount)}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Menu principal", callback_data="menu_main")]
        ]),
        parse_mode="Markdown",
    )

    context.user_data.pop("transfer_src", None)
    context.user_data.pop("transfer_dst", None)
    context.user_data.pop("transfer_amount", None)
    context.user_data.pop("awaiting_transfer_amount", None)


# ─── PAY CREDIT CARD ───
async def start_pay_card(query, context, bank_id):
    bd = await api_get(f"/api/banks/{bank_id}/data")
    cards = [c for c in bd.get("credit_cards", []) if c["used_credit"] > 0]

    if not cards:
        await query.edit_message_text(
            "*No hay tarjetas con deuda en este banco.*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Volver", callback_data=f"bank_{bank_id}")]
            ]),
            parse_mode="Markdown",
        )
        return

    context.user_data["pay_cards"] = {c["id"]: c for c in cards}
    context.user_data["pay_bank_id"] = bank_id
    keyboard = []
    for c in cards:
        pct = credit_pct(c["used_credit"], c["credit_limit"])
        keyboard.append([
            InlineKeyboardButton(
                f"💳 {c['name']}: {fmt_money(c['used_credit'])} ({pct:.0f}%)",
                callback_data=f"paycard_{c['id']}",
            )
        ])
    keyboard.append([InlineKeyboardButton("◀️ Volver", callback_data=f"bank_{bank_id}")])

    await query.edit_message_text(
        "*Pagar Tarjeta*\nElige la tarjeta a pagar:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def pay_card_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("paycard_"):
        card_id = data.replace("paycard_", "")
        card = context.user_data.get("pay_cards", {}).get(card_id)
        context.user_data["pay_card"] = card

        accounts = await api_get("/api/accounts/all")
        context.user_data["pay_accounts"] = {a["id"]: a for a in accounts}

        keyboard = []
        for a in accounts:
            banks = context.user_data.get("banks", {})
            bank_name = "Banco"
            for b in banks.values():
                if b["id"] == a["bank_id"]:
                    bank_name = b["name"]
                    break
            keyboard.append([
                InlineKeyboardButton(
                    f"{bank_name} - {a['name']}: {fmt_money(a['balance'])}",
                    callback_data=f"paysrc_{a['id']}",
                )
            ])
        bank_id = context.user_data.get("pay_bank_id")
        keyboard.append([InlineKeyboardButton("◀️ Volver", callback_data=f"bank_{bank_id}")])

        await query.edit_message_text(
            f"*Pagar {card['name']}*\nDeuda: {fmt_money(card['used_credit'])}\n\n"
            f"Elige la cuenta para pagar:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    elif data.startswith("paysrc_"):
        account_id = data.replace("paysrc_", "")
        context.user_data["pay_src_account"] = account_id
        card = context.user_data.get("pay_card")

        keyboard = [
            [InlineKeyboardButton(
                f"Pagar total: {fmt_money(card['used_credit'])}",
                callback_data="payamt_total",
            )],
            [InlineKeyboardButton(
                "Pago parcial",
                callback_data="payamt_partial",
            )],
        ]
        await query.edit_message_text(
            f"*Pagar {card['name']}*\nDeuda: {fmt_money(card['used_credit'])}\n\n"
            f"Cuanto quieres pagar?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    elif data == "payamt_total":
        card = context.user_data.get("pay_card")
        context.user_data["pay_amount"] = card["used_credit"]
        await confirm_pay(query, context)

    elif data == "payamt_partial":
        await query.edit_message_text(
            "*Escribe el monto a pagar (solo numeros):*",
            parse_mode="Markdown",
        )
        context.user_data["awaiting_pay_amount"] = True

    elif data == "confirm_pay":
        await execute_pay(query, context)

    elif data == "cancel_pay":
        bank_id = context.user_data.get("pay_bank_id")
        await show_bank_detail(query, context, f"bank_{bank_id}")


async def confirm_pay(query, context):
    card = context.user_data.get("pay_card")
    amount = context.user_data.get("pay_amount")
    accounts = context.user_data.get("pay_accounts", {})
    src_account = accounts.get(context.user_data.get("pay_src_account"), {})

    keyboard = [
        [InlineKeyboardButton("✅ Confirmar pago", callback_data="confirm_pay")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_pay")],
    ]

    await query.edit_message_text(
        f"*Confirmar pago de tarjeta*\n\n"
        f"💳 Tarjeta: {card['name']}\n"
        f"💰 Pago: {fmt_money(amount)}\n"
        f"🏦 Cuenta: {src_account.get('name', 'N/A')}\n"
        f"📊 Deuda restante: {fmt_money(float(card['used_credit']) - amount)}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def execute_pay(query, context):
    card = context.user_data.get("pay_card")
    amount = context.user_data.get("pay_amount")
    src_account_id = context.user_data.get("pay_src_account")
    account = context.user_data.get("pay_accounts", {}).get(src_account_id, {})

    if float(account.get("balance", 0)) < amount:
        await query.edit_message_text(
            "*Saldo insuficiente en la cuenta.*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Volver", callback_data="menu_main")]
            ]),
            parse_mode="Markdown",
        )
        return

    await api_post("/api/transactions", {
        "bank_id": card["bank_id"],
        "account_id": src_account_id,
        "type": "gasto",
        "amount": amount,
        "merchant": f"Pago tarjeta {card['name']}",
        "category": "Pago tarjeta",
        "description": f"Pago de tarjeta via Telegram",
    })

    await api_post("/api/transactions", {
        "bank_id": card["bank_id"],
        "credit_card_id": card["id"],
        "type": "ingreso",
        "amount": amount,
        "merchant": "Pago recibido",
        "category": "Pago tarjeta",
        "description": f"Pago desde {account.get('name', 'cuenta')} via Telegram",
    })

    new_used = float(card["used_credit"]) - amount
    pct = credit_pct(new_used, card["credit_limit"])

    await query.edit_message_text(
        f"*Pago realizado*\n\n"
        f"💳 {card['name']}: {fmt_money(new_used)} / {fmt_money(card['credit_limit'])} ({pct:.0f}%)\n"
        f"{credit_status(pct)}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Menu principal", callback_data="menu_main")]
        ]),
        parse_mode="Markdown",
    )

    context.user_data.pop("pay_card", None)
    context.user_data.pop("pay_src_account", None)
    context.user_data.pop("pay_amount", None)
    context.user_data.pop("pay_bank_id", None)


# ─── INCOME ───
async def start_income(query, context, bank_id):
    bd = await api_get(f"/api/banks/{bank_id}/data")
    accounts = bd.get("accounts", [])

    if not accounts:
        await query.edit_message_text(
            "*No hay cuentas en este banco.*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Volver", callback_data=f"bank_{bank_id}")]
            ]),
            parse_mode="Markdown",
        )
        return

    context.user_data["income_accounts"] = {a["id"]: a for a in accounts}
    context.user_data["income_bank_id"] = bank_id
    keyboard = []
    for a in accounts:
        keyboard.append([
            InlineKeyboardButton(
                f"💰 {a['name']}: {fmt_money(a['balance'])}",
                callback_data=f"incdst_{a['id']}",
            )
        ])
    keyboard.append([InlineKeyboardButton("◀️ Volver", callback_data=f"bank_{bank_id}")])

    await query.edit_message_text(
        "*Registrar Ingreso*\nElige la cuenta destino:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def income_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("incdst_"):
        account_id = data.replace("incdst_", "")
        context.user_data["income_account"] = account_id
        await query.edit_message_text(
            "*Escribe el monto del ingreso (solo numeros):*",
            parse_mode="Markdown",
        )
        context.user_data["awaiting_income_amount"] = True

    elif data == "confirm_income":
        await execute_income(query, context)

    elif data == "cancel_income":
        bank_id = context.user_data.get("income_bank_id")
        await show_bank_detail(query, context, f"bank_{bank_id}")


async def confirm_income_msg(target, context):
    amount = context.user_data.get("income_amount")
    account_id = context.user_data.get("income_account")
    accounts = context.user_data.get("income_accounts", {})
    account = accounts.get(account_id, {})

    keyboard = [
        [InlineKeyboardButton("✅ Confirmar", callback_data="confirm_income")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_income")],
    ]

    text = (
        f"*Confirmar ingreso*\n\n"
        f"💰 Cuenta: {account.get('name', 'N/A')}\n"
        f"💵 Monto: {fmt_money(amount)}\n"
        f"📊 Saldo nuevo: {fmt_money(float(account.get('balance', 0)) + amount)}"
    )
    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(target, "edit_message_text"):
        await target.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await target.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def execute_income(query, context):
    amount = context.user_data.get("income_amount")
    account_id = context.user_data.get("income_account")
    accounts = context.user_data.get("income_accounts", {})
    account = accounts.get(account_id, {})

    await api_post("/api/transactions", {
        "bank_id": account["bank_id"],
        "account_id": account_id,
        "type": "ingreso",
        "amount": amount,
        "merchant": "Ingreso manual",
        "category": "Ingreso",
        "description": "Ingreso registrado via Telegram",
    })

    new_balance = float(account["balance"]) + amount

    await query.edit_message_text(
        f"*Ingreso registrado*\n\n"
        f"💰 {account['name']}: {fmt_money(new_balance)}\n"
        f"💵 Ingreso: {fmt_money(amount)}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Menu principal", callback_data="menu_main")]
        ]),
        parse_mode="Markdown",
    )

    context.user_data.pop("income_account", None)
    context.user_data.pop("income_amount", None)
    context.user_data.pop("income_accounts", None)
    context.user_data.pop("income_bank_id", None)


# ─── EXPENSE (GASTO) ───
async def start_expense(query, context, bank_id):
    bd = await api_get(f"/api/banks/{bank_id}/data")
    cards = bd.get("credit_cards", [])
    accounts = bd.get("accounts", [])

    if not cards and not accounts:
        await query.edit_message_text(
            "*No hay cuentas ni tarjetas en este banco.*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Volver", callback_data=f"bank_{bank_id}")]
            ]),
            parse_mode="Markdown",
        )
        return

    context.user_data["expense_bank_id"] = bank_id
    context.user_data["expense_cards"] = {c["id"]: c for c in cards}
    context.user_data["expense_accounts"] = {a["id"]: a for a in accounts}
    keyboard = []
    for c in cards:
        pct = credit_pct(c["used_credit"], c["credit_limit"])
        available = float(c["credit_limit"]) - float(c["used_credit"])
        keyboard.append([
            InlineKeyboardButton(
                f"💳 {c['name']}: {fmt_money(available)} disponible",
                callback_data=f"expcard_{c['id']}",
            )
        ])
    for a in accounts:
        keyboard.append([
            InlineKeyboardButton(
                f"💰 {a['name']}: {fmt_money(a['balance'])}",
                callback_data=f"expacc_{a['id']}",
            )
        ])
    keyboard.append([InlineKeyboardButton("◀️ Volver", callback_data=f"bank_{bank_id}")])

    await query.edit_message_text(
        "*Registrar Gasto*\nElige de donde sale el dinero:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def expense_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    print(f"EXPENSE CALLBACK: {data}, user_data keys: {list(context.user_data.keys())}", flush=True)

    try:
        if data.startswith("expcard_"):
            card_id = data.replace("expcard_", "")
            card = context.user_data.get("expense_cards", {}).get(card_id)
            context.user_data["expense_card"] = card
            context.user_data["expense_type"] = "credit_card"

            pct_clp = credit_pct(card["used_credit"], card["credit_limit"])
            avail_clp = float(card["credit_limit"]) - float(card["used_credit"])
            pct_usd = credit_pct(card.get("used_credit_usd", 0), card.get("credit_limit_usd", 0))
            avail_usd = float(card.get("credit_limit_usd", 0)) - float(card.get("used_credit_usd", 0))

            text = f"*{card['name']}* (Credito)\n\n"
            if float(card.get("credit_limit", 0)) > 0:
                text += f"🇨🇱 CLP: {fmt_money(card['used_credit'])} / {fmt_money(card['credit_limit'])} ({pct_clp:.0f}%) - Disp: {fmt_money(avail_clp)}\n"
            if float(card.get("credit_limit_usd", 0)) > 0:
                text += f"🇺🇸 USD: {fmt_money(card.get('used_credit_usd', 0))} / {fmt_money(card.get('credit_limit_usd', 0))} ({pct_usd:.0f}%) - Disp: {fmt_money(avail_usd)}\n"
            text += "\nEscribe el monto del gasto (solo numeros):"

            await query.edit_message_text(
                text,
                parse_mode="Markdown",
            )
            context.user_data["awaiting_expense_amount"] = True

        elif data.startswith("expacc_"):
            account_id = data.replace("expacc_", "")
            account = context.user_data.get("expense_accounts", {}).get(account_id)
            context.user_data["expense_card"] = account
            context.user_data["expense_type"] = "account"

            await query.edit_message_text(
                f"*{account['name']}* (Debito)\n\n"
                f"Saldo: {fmt_money(account['balance'])}\n\n"
                f"Escribe el monto del gasto (solo numeros):",
                parse_mode="Markdown",
            )
            context.user_data["awaiting_expense_amount"] = True

        elif data == "exec_expense":
            await execute_expense(query, context)

        elif data == "cancel_expense":
            bank_id = context.user_data.get("expense_bank_id")
            await show_bank_detail(query, context, f"bank_{bank_id}")
    except Exception as e:
        print(f"ERROR in expense_callback: {e}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        try:
            await query.edit_message_text("Error. Intenta con /start")
        except Exception:
            pass


async def execute_expense(query, context):
    item = context.user_data.get("expense_card")
    amount = context.user_data.get("expense_amount")
    exp_type = context.user_data.get("expense_type")
    currency = context.user_data.get("expense_currency", "CLP")
    desc = context.user_data.get("expense_description", "Gasto manual")

    if exp_type == "credit_card":
        await api_post("/api/transactions", {
            "bank_id": item["bank_id"],
            "credit_card_id": item["id"],
            "type": "gasto",
            "amount": amount,
            "currency": currency,
            "merchant": desc,
            "category": "Manual",
            "description": desc,
        })
        if currency == "USD":
            new_used = float(item.get("used_credit_usd", 0)) + amount
            limit = float(item.get("credit_limit_usd", 0))
            new_pct = credit_pct(new_used, limit)
            available = limit - new_used

            text = (
                f"*Gasto registrado*\n\n"
                f"💳 {item['name']}\n"
                f"📝 {desc}\n"
                f"💵 Gasto: ${amount:.2f} USD\n"
                f"📊 Deuda: ${new_used:.2f} / ${limit:.2f} USD ({new_pct:.0f}%)\n"
                f"💰 Disponible: ${available:.2f} USD\n\n"
            )
            if new_pct >= 30:
                text += "🔴 ALERTA: Superaste el 30%. No uses mas esta tarjeta."
            elif new_pct >= 20:
                remaining = limit * 0.3 - new_used
                text += f"🟡 En rango ideal. Puedes usar ${max(0, remaining):.2f} USD mas."
            else:
                remaining = limit * 0.3 - new_used
                text += f"✅ Vas bien. Puedes usar ${remaining:.2f} USD mas antes del 30%."
        else:
            new_used = float(item.get("used_credit", 0)) + amount
            limit = float(item.get("credit_limit", 0))
            new_pct = credit_pct(new_used, limit)
            available = limit - new_used

            text = (
                f"*Gasto registrado*\n\n"
                f"💳 {item['name']}\n"
                f"📝 {desc}\n"
                f"💵 Gasto: {fmt_money(amount)} CLP\n"
                f"📊 Deuda: {fmt_money(new_used)} / {fmt_money(limit)} ({new_pct:.0f}%)\n"
                f"💰 Disponible: {fmt_money(available)} CLP\n\n"
            )
            if new_pct >= 30:
                text += "🔴 ALERTA: Superaste el 30%. No uses mas esta tarjeta."
            elif new_pct >= 20:
                remaining = limit * 0.3 - new_used
                text += f"🟡 En rango ideal. Puedes usar {fmt_money(max(0, remaining))} mas."
            else:
                remaining = limit * 0.3 - new_used
                text += f"✅ Vas bien. Puedes usar {fmt_money(remaining)} mas antes del 30%."
    else:
        if float(item["balance"]) < amount:
            await query.edit_message_text(
                f"*Saldo insuficiente*\n\n"
                f"💰 {item['name']}: {fmt_money(item['balance'])}\n"
                f"💵 Gasto: {fmt_money(amount)}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Volver", callback_data="menu_main")]
                ]),
                parse_mode="Markdown",
            )
            return

        await api_post("/api/transactions", {
            "bank_id": item["bank_id"],
            "account_id": item["id"],
            "type": "gasto",
            "amount": amount,
            "merchant": desc,
            "category": "Manual",
            "description": desc,
        })
        new_balance = float(item["balance"]) - amount
        text = (
            f"*Gasto registrado*\n\n"
            f"💰 {item['name']}\n"
            f"💵 Gasto: {fmt_money(amount)}\n"
            f"📊 Saldo: {fmt_money(new_balance)}\n\n"
            f"✅ Descontado de tu cuenta de debito."
        )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Menu principal", callback_data="menu_main")]
        ]),
        parse_mode="Markdown",
    )

    context.user_data.pop("expense_card", None)
    context.user_data.pop("expense_amount", None)
    context.user_data.pop("expense_type", None)
    context.user_data.pop("expense_description", None)
    context.user_data.pop("expense_cards", None)
    context.user_data.pop("expense_accounts", None)
    context.user_data.pop("expense_bank_id", None)
    context.user_data.pop("awaiting_expense_amount", None)
    context.user_data.pop("awaiting_expense_description", None)


async def ask_expense_description(target, context):
    if hasattr(target, "reply_text"):
        await target.reply_text(
            "*Escribe que compraste* (ej: Bolas de queso/jalapeno):",
            parse_mode="Markdown",
        )
    else:
        await target.edit_message_text(
            "*Escribe que compraste* (ej: Bolas de queso/jalapeno):",
            parse_mode="Markdown",
        )
    context.user_data["awaiting_expense_description"] = True


async def currency_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("expcurr_"):
        currency = data.replace("expcurr_", "")
        context.user_data["expense_currency"] = currency
        context.user_data["awaiting_expense_currency"] = False
        item = context.user_data.get("expense_card", {})
        amount = context.user_data.get("expense_amount")

        if currency == "USD":
            used = float(item.get("used_credit_usd", 0))
            limit = float(item.get("credit_limit_usd", 0))
        else:
            used = float(item.get("used_credit", 0))
            limit = float(item.get("credit_limit", 0))

        if used + amount > limit:
            sym = "$" if currency == "CLP" else "$"
            fmt = fmt_money if currency == "CLP" else lambda x: f"${x:.2f}"
            await query.edit_message_text(
                f"*Excede el limite*\n\n"
                f"💳 {item.get('name', 'N/A')}\n"
                f"💵 Gasto: {fmt(amount)} {currency}\n"
                f"📊 Limite: {fmt(limit)} {currency}",
                parse_mode="Markdown",
            )
            return

        await query.edit_message_text(
            "*Escribe que compraste* (ej: Bolas de queso/jalapeno):",
            parse_mode="Markdown",
        )
        context.user_data["awaiting_expense_description"] = True


# ─── SUMMARY ───
async def show_summary(query, context):
    banks = await api_get("/api/banks")
    text = "*RESUMEN DE CREDITO*\n\n"
    total_used = 0
    total_limit = 0

    for b in banks:
        bd = await api_get(f"/api/banks/{b['id']}/data")
        for c in bd.get("credit_cards", []):
            used = c["used_credit"]
            limit = c["credit_limit"]
            pct = credit_pct(used, limit)
            total_used += used
            total_limit += limit
            emoji = credit_emoji(pct)
            text += f"{emoji} *{b['name']}* - {c['name']}\n"
            text += f"   {fmt_money(used)} / {fmt_money(limit)} ({pct:.0f}%)\n\n"

    if total_limit > 0:
        total_pct = credit_pct(total_used, total_limit)
        text += f"*TOTAL:* {fmt_money(total_used)} / {fmt_money(total_limit)} ({total_pct:.0f}%)\n"
        text += credit_status(total_pct)

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Menu principal", callback_data="menu_main")]
        ]),
        parse_mode="Markdown",
    )


# ─── HELP ───
async def show_help(query):
    await query.edit_message_text(
        "*CreditoSubaru - Ayuda*\n\n"
        "🏦 *Ver Bancos* - Ver cuentas y tarjetas por banco\n"
        "📊 *Mi Resumen* - Uso global de credito\n"
        "💸 *Transferir* - Mover dinero entre cuentas\n\n"
        "Dentro de cada banco:\n"
        "🛒 Gasto - Registrar uso de tarjeta de credito\n"
        "📜 Historial - Ultimos movimientos\n"
        "💳 Pagar Tarjeta - Pagar deuda con una cuenta\n"
        "📥 Ingreso - Agregar dinero a una cuenta\n\n"
        "*Objetivo:* Usar 20-30% del credito\n"
        "para mejorar tu historial crediticio.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Menu principal", callback_data="menu_main")]
        ]),
        parse_mode="Markdown",
    )


# ─── TEXT HANDLER (amounts) ───
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace(".", "").replace(",", "").strip()

    if context.user_data.get("awaiting_transfer_amount"):
        try:
            amount = float(text)
        except ValueError:
            await update.message.reply_text("Monto invalido. Escribe solo numeros.")
            return
        context.user_data["awaiting_transfer_amount"] = False
        context.user_data["transfer_amount"] = amount

        src_id = context.user_data.get("transfer_src")
        dst_id = context.user_data.get("transfer_dst")
        accounts = context.user_data.get("all_accounts", {})
        src = accounts.get(src_id, {})
        dst = accounts.get(dst_id, {})

        keyboard = [
            [InlineKeyboardButton("✅ Confirmar", callback_data="confirm_transfer")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_transfer")],
        ]

        await update.message.reply_text(
            f"*Confirmar transferencia*\n\n"
            f"📤 {src.get('name', 'N/A')}: {fmt_money(float(src.get('balance', 0)))}\n"
            f"📥 {dst.get('name', 'N/A')}: {fmt_money(float(dst.get('balance', 0)))}\n\n"
            f"💵 Monto: {fmt_money(amount)}\n"
            f"📊 Saldo origen despues: {fmt_money(float(src.get('balance', 0)) - amount)}\n"
            f"📊 Saldo destino despues: {fmt_money(float(dst.get('balance', 0)) + amount)}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    elif context.user_data.get("awaiting_pay_amount"):
        try:
            amount = float(text)
        except ValueError:
            await update.message.reply_text("Monto invalido. Escribe solo numeros.")
            return
        context.user_data["awaiting_pay_amount"] = False
        context.user_data["pay_amount"] = amount

        card = context.user_data.get("pay_card", {})
        account_id = context.user_data.get("pay_src_account")
        accounts = context.user_data.get("pay_accounts", {})
        account = accounts.get(account_id, {})

        keyboard = [
            [InlineKeyboardButton("✅ Confirmar pago", callback_data="confirm_pay")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_pay")],
        ]

        await update.message.reply_text(
            f"*Confirmar pago*\n\n"
            f"💳 Tarjeta: {card.get('name', 'N/A')}\n"
            f"💰 Pago: {fmt_money(amount)}\n"
            f"🏦 Cuenta: {account.get('name', 'N/A')}\n"
            f"📊 Deuda restante: {fmt_money(float(card.get('used_credit', 0)) - amount)}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    elif context.user_data.get("awaiting_income_amount"):
        try:
            amount = float(text)
        except ValueError:
            await update.message.reply_text("Monto invalido. Escribe solo numeros.")
            return
        context.user_data["awaiting_income_amount"] = False
        context.user_data["income_amount"] = amount
        try:
            await confirm_income_msg(update.message, context)
        except Exception as e:
            print(f"ERROR in confirm_income_msg: {e}", flush=True)
            await update.message.reply_text(
                "⚠️ Error al procesar. Intenta con /start"
            )

    elif context.user_data.get("awaiting_expense_amount"):
        try:
            amount = float(text)
        except ValueError:
            await update.message.reply_text("Monto invalido. Escribe solo numeros.")
            return
        context.user_data["awaiting_expense_amount"] = False
        context.user_data["expense_amount"] = amount
        try:
            item = context.user_data.get("expense_card", {})
            exp_type = context.user_data.get("expense_type")

            if exp_type == "credit_card":
                has_usd = float(item.get("credit_limit_usd", 0)) > 0
                if has_usd:
                    keyboard = [
                        [InlineKeyboardButton("🇨🇱 Pesos Chilenos (CLP)", callback_data="expcurr_CLP")],
                        [InlineKeyboardButton("🇺🇸 Dolares (USD)", callback_data="expcurr_USD")],
                    ]
                    await update.message.reply_text(
                        "En que moneda?",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="Markdown",
                    )
                    context.user_data["awaiting_expense_currency"] = True
                else:
                    context.user_data["expense_currency"] = "CLP"
                    await ask_expense_description(update.message, context)
            else:
                context.user_data["expense_currency"] = "CLP"
                balance = float(item.get("balance", 0))
                if balance < amount:
                    await update.message.reply_text(
                        f"*Saldo insuficiente*\n\n"
                        f"💰 {item.get('name', 'N/A')}: {fmt_money(balance)}\n"
                        f"💵 Gasto: {fmt_money(amount)}",
                        parse_mode="Markdown",
                    )
                    return
                await ask_expense_description(update.message, context)
        except Exception as e:
            print(f"ERROR in expense flow: {e}", flush=True)
            await update.message.reply_text(
                "⚠️ Error al procesar. Intenta con /start"
            )

    elif context.user_data.get("awaiting_expense_currency"):
        return

    elif context.user_data.get("awaiting_expense_description"):
        context.user_data["awaiting_expense_description"] = False
        context.user_data["expense_description"] = text
        try:
            item = context.user_data.get("expense_card", {})
            exp_type = context.user_data.get("expense_type")
            amount = context.user_data.get("expense_amount")
            currency = context.user_data.get("expense_currency", "CLP")
            desc = text

            if exp_type == "credit_card":
                if currency == "USD":
                    new_used = float(item.get("used_credit_usd", 0)) + amount
                    limit = float(item.get("credit_limit_usd", 0))
                    new_pct = credit_pct(new_used, limit)
                    available = limit - new_used

                    keyboard = [
                        [InlineKeyboardButton("✅ Confirmar gasto", callback_data="exec_expense")],
                        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_expense")],
                    ]

                    await update.message.reply_text(
                        f"*Confirmar gasto*\n\n"
                        f"💳 {item.get('name', 'N/A')} (Credito)\n"
                        f"📝 {desc}\n"
                        f"💵 Monto: ${amount:.2f} USD\n"
                        f"📊 Deuda nueva: ${new_used:.2f} / ${limit:.2f} USD ({new_pct:.0f}%)\n"
                        f"{credit_status(new_pct)}",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="Markdown",
                    )
                else:
                    new_used = float(item.get("used_credit", 0)) + amount
                    limit = float(item.get("credit_limit", 0))
                    new_pct = credit_pct(new_used, limit)
                    available = limit - new_used

                    keyboard = [
                        [InlineKeyboardButton("✅ Confirmar gasto", callback_data="exec_expense")],
                        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_expense")],
                    ]

                    await update.message.reply_text(
                        f"*Confirmar gasto*\n\n"
                        f"💳 {item.get('name', 'N/A')} (Credito)\n"
                        f"📝 {desc}\n"
                        f"💵 Monto: {fmt_money(amount)} CLP\n"
                        f"📊 Deuda nueva: {fmt_money(new_used)} / {fmt_money(limit)} ({new_pct:.0f}%)\n"
                        f"{credit_status(new_pct)}",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="Markdown",
                    )
            else:
                new_balance = float(item.get("balance", 0)) - amount

                keyboard = [
                    [InlineKeyboardButton("✅ Confirmar gasto", callback_data="exec_expense")],
                    [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_expense")],
                ]

                await update.message.reply_text(
                    f"*Confirmar gasto*\n\n"
                    f"💰 {item.get('name', 'N/A')} (Debito)\n"
                    f"📝 {desc}\n"
                    f"💵 Monto: {fmt_money(amount)}\n"
                    f"📊 Saldo nuevo: {fmt_money(new_balance)}",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown",
                )
        except Exception as e:
            print(f"ERROR in expense confirm: {e}", flush=True)
            await update.message.reply_text(
                "⚠️ Error al procesar. Intenta con /start"
            )


# ─── MAIN ───
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import traceback
    print(f"BOT ERROR: {context.error}", flush=True)
    print(f"TRACEBACK: {traceback.format_exc()}", flush=True)
    if update and update.callback_query:
        print(f"CALLBACK DATA: {update.callback_query.data}", flush=True)
    print(f"USER_DATA: {dict(context.user_data)}", flush=True)
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Ocurrio un error. Intenta de nuevo con /start"
            )
        except Exception:
            pass


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("ERROR: Define TELEGRAM_BOT_TOKEN", flush=True)
        return

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^(menu_|bank_|action_)"))
    app.add_handler(CallbackQueryHandler(transfer_callback, pattern=r"^(tsrc_|tdst_|confirm_transfer|cancel_transfer)"))
    app.add_handler(CallbackQueryHandler(pay_card_callback, pattern=r"^(paycard_|paysrc_|payamt_|confirm_pay|cancel_pay)"))
    app.add_handler(CallbackQueryHandler(income_callback, pattern=r"^(incdst_|confirm_income|cancel_income)"))
    app.add_handler(CallbackQueryHandler(expense_callback, pattern=r"^(expcard_|expacc_|exec_expense|cancel_expense)"))
    app.add_handler(CallbackQueryHandler(currency_callback, pattern=r"^expcurr_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_error_handler(error_handler)

    print("Bot started!", flush=True)
    app.run_polling()


if __name__ == "__main__":
    main()
