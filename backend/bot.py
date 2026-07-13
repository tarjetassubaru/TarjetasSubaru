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


def fmt(amount: float) -> str:
    return f"${amount:,.0f}".replace(",", ".")


def fmt_usd(amount: float) -> str:
    return f"${amount:,.2f}"


def pct(used: float, limit: float) -> float:
    return (used / limit * 100) if limit > 0 else 0


def bar(p: float, size: int = 10) -> str:
    filled = min(int(p / 100 * size), size)
    return "█" * filled + "░" * (size - filled)


def status_emoji(p: float) -> str:
    if p >= 30:
        return "🔴"
    elif p >= 20:
        return "🟡"
    return "🟢"


def status_text(p: float) -> str:
    if p >= 30:
        return "ALERTA: Usaste mas del 30%"
    elif p >= 20:
        return "Rango ideal (20-30%)"
    return "Bajo el 20% - Vas bien"


async def fetch_all_data():
    banks = await api_get("/api/banks")
    all_accounts = await api_get("/api/accounts/all")
    bank_data = {}
    for b in banks:
        bank_data[b["id"]] = await api_get(f"/api/banks/{b['id']}/data")
    return banks, all_accounts, bank_data


# ─── /start ───
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    try:
        banks, all_accounts, bank_data = await fetch_all_data()
    except Exception as e:
        print(f"ERROR in /start: {e}", flush=True)
        await update.message.reply_text("Error al conectar. Intenta de nuevo.")
        return

    context.user_data["banks"] = {b["id"]: b for b in banks}
    context.user_data["all_accounts"] = {a["id"]: a for a in all_accounts}

    total_balance = sum(float(a["balance"]) for a in all_accounts)

    total_clp_used = 0
    total_clp_limit = 0
    total_usd_used = 0
    total_usd_limit = 0

    for bd in bank_data.values():
        for c in bd.get("credit_cards", []):
            total_clp_used += float(c["used_credit"])
            total_clp_limit += float(c["credit_limit"])
            total_usd_used += float(c.get("used_credit_usd", 0))
            total_usd_limit += float(c.get("credit_limit_usd", 0))

    p_clp = pct(total_clp_used, total_clp_limit)
    p_usd = pct(total_usd_used, total_usd_limit)

    text = "━━━━━━━━━━━━━━━━━━━━\n"
    text += "💰 *CUENTAS*\n"
    text += f"   Total: *{fmt(total_balance)}*\n"

    for a in all_accounts:
        bname = "Banco"
        for b in banks:
            if b["id"] == a["bank_id"]:
                bname = b["name"]
                break
        text += f"   • {a['name']} ({bname}): {fmt(a['balance'])}\n"

    text += "\n━━━━━━━━━━━━━━━━━━━━\n"
    text += "💳 *CREDITO CLP*\n"
    if total_clp_limit > 0:
        text += f"   {bar(p_clp)} {p_clp:.0f}%\n"
        text += f"   Usado: {fmt(total_clp_used)} / {fmt(total_clp_limit)}\n"
        text += f"   {status_emoji(p_clp)} {status_text(p_clp)}\n"
    else:
        text += "   Sin credito CLP\n"

    if total_usd_limit > 0:
        text += "\n━━━━━━━━━━━━━━━━━━━━\n"
        text += "💵 *CREDITO USD*\n"
        text += f"   {bar(p_usd)} {p_usd:.0f}%\n"
        text += f"   Usado: {fmt_usd(total_usd_used)} / {fmt_usd(total_usd_limit)}\n"
        text += f"   {status_emoji(p_usd)} {status_text(p_usd)}\n"

    text += "\n━━━━━━━━━━━━━━━━━━━━"

    keyboard = [
        [InlineKeyboardButton("🏦 Mis Bancos", callback_data="menu_banks")],
        [InlineKeyboardButton("📊 Resumen Credito", callback_data="menu_summary")],
        [InlineKeyboardButton("💸 Transferir", callback_data="menu_transfer")],
        [InlineKeyboardButton("❓ Ayuda", callback_data="menu_help")],
    ]

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def show_main_menu(query, context):
    try:
        banks, all_accounts, bank_data = await fetch_all_data()
    except Exception:
        await query.edit_message_text("Error. Intenta con /start")
        return

    context.user_data["banks"] = {b["id"]: b for b in banks}
    context.user_data["all_accounts"] = {a["id"]: a for a in all_accounts}

    total_balance = sum(float(a["balance"]) for a in all_accounts)

    total_clp_used = 0
    total_clp_limit = 0
    total_usd_used = 0
    total_usd_limit = 0

    for bd in bank_data.values():
        for c in bd.get("credit_cards", []):
            total_clp_used += float(c["used_credit"])
            total_clp_limit += float(c["credit_limit"])
            total_usd_used += float(c.get("used_credit_usd", 0))
            total_usd_limit += float(c.get("credit_limit_usd", 0))

    p_clp = pct(total_clp_used, total_clp_limit)
    p_usd = pct(total_usd_used, total_usd_limit)

    text = "━━━━━━━━━━━━━━━━━━━━\n"
    text += "💰 *CUENTAS*\n"
    text += f"   Total: *{fmt(total_balance)}*\n"

    for a in all_accounts:
        bname = "Banco"
        for b in banks:
            if b["id"] == a["bank_id"]:
                bname = b["name"]
                break
        text += f"   • {a['name']} ({bname}): {fmt(a['balance'])}\n"

    text += "\n━━━━━━━━━━━━━━━━━━━━\n"
    text += "💳 *CREDITO CLP*\n"
    if total_clp_limit > 0:
        text += f"   {bar(p_clp)} {p_clp:.0f}%\n"
        text += f"   Usado: {fmt(total_clp_used)} / {fmt(total_clp_limit)}\n"
        text += f"   {status_emoji(p_clp)} {status_text(p_clp)}\n"
    else:
        text += "   Sin credito CLP\n"

    if total_usd_limit > 0:
        text += "\n━━━━━━━━━━━━━━━━━━━━\n"
        text += "💵 *CREDITO USD*\n"
        text += f"   {bar(p_usd)} {p_usd:.0f}%\n"
        text += f"   Usado: {fmt_usd(total_usd_used)} / {fmt_usd(total_usd_limit)}\n"
        text += f"   {status_emoji(p_usd)} {status_text(p_usd)}\n"

    text += "\n━━━━━━━━━━━━━━━━━━━━"

    keyboard = [
        [InlineKeyboardButton("🏦 Mis Bancos", callback_data="menu_banks")],
        [InlineKeyboardButton("📊 Resumen Credito", callback_data="menu_summary")],
        [InlineKeyboardButton("💸 Transferir", callback_data="menu_transfer")],
        [InlineKeyboardButton("❓ Ayuda", callback_data="menu_help")],
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# ─── MAIN MENU CALLBACKS ───
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    try:
        if data == "menu_banks":
            await show_banks_list(query, context)
        elif data == "menu_summary":
            await show_summary(query, context)
        elif data == "menu_transfer":
            await start_transfer(query, context, all_accounts=True)
        elif data == "menu_help":
            await show_help(query)
        elif data == "menu_main":
            await show_main_menu(query, context)
        elif data.startswith("bank_"):
            await show_bank_detail(query, context, data)
        elif data.startswith("action_"):
            await handle_bank_action(query, context, data)
    except Exception as e:
        print(f"ERROR in menu_callback: {e}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        try:
            await query.edit_message_text("Error. Intenta con /start")
        except Exception:
            pass


# ─── BANKS LIST ───
async def show_banks_list(query, context):
    banks = await api_get("/api/banks")
    if not banks:
        await query.edit_message_text("No hay bancos registrados.")
        return

    context.user_data["banks"] = {b["id"]: b for b in banks}

    text = "🏦 *MIS BANCOS*\n"
    text += "Selecciona un banco para ver detalles\n\n"

    for b in banks:
        bd = await api_get(f"/api/banks/{b['id']}/data")
        accounts = bd.get("accounts", [])
        cards = bd.get("credit_cards", [])

        total_acc = sum(float(a["balance"]) for a in accounts)
        total_clp_debt = sum(float(c["used_credit"]) for c in cards)
        total_usd_debt = sum(float(c.get("used_credit_usd", 0)) for c in cards)

        text += f"*{b['name']}*\n"
        if total_acc > 0:
            text += f"   💰 Cuentas: {fmt(total_acc)}\n"
        if total_clp_debt > 0:
            text += f"   💳 Deuda CLP: {fmt(total_clp_debt)}\n"
        if total_usd_debt > 0:
            text += f"   💳 Deuda USD: {fmt_usd(total_usd_debt)}\n"
        if total_acc == 0 and total_clp_debt == 0 and total_usd_debt == 0:
            text += f"   (sin movimientos)\n"
        text += "\n"

    keyboard = []
    for b in banks:
        keyboard.append([InlineKeyboardButton(f"→ {b['name']}", callback_data=f"bank_{b['id']}")])
    keyboard.append([InlineKeyboardButton("◀️ Volver", callback_data="menu_main")])

    await query.edit_message_text(
        text,
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

        text = f"🏦 *{bank['name'].upper()}*\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n"

        if accounts:
            text += "💰 *CUENTAS*\n"
            for a in accounts:
                text += f"   • {a['name']}: *{fmt(a['balance'])}*\n"
                if a.get("interest_rate", 0) > 0:
                    text += f"     📈 {a['interest_rate']}% anual\n"

        if cards:
            for c in cards:
                p_c = pct(c["used_credit"], c["credit_limit"])
                p_u = pct(c.get("used_credit_usd", 0), c.get("credit_limit_usd", 0))

                text += f"\n💳 *{c['name']}*\n"

                if float(c["credit_limit"]) > 0:
                    avail = float(c["credit_limit"]) - float(c["used_credit"])
                    text += f"   🇨🇱 CLP {bar(p_c)} {p_c:.0f}%\n"
                    text += f"   Deuda: {fmt(c['used_credit'])} / {fmt(c['credit_limit'])}\n"
                    text += f"   Disp: {fmt(avail)}\n"

                if float(c.get("credit_limit_usd", 0)) > 0:
                    avail_usd = float(c.get("credit_limit_usd", 0)) - float(c.get("used_credit_usd", 0))
                    text += f"   🇺🇸 USD {bar(p_u)} {p_u:.0f}%\n"
                    text += f"   Deuda: {fmt_usd(c.get('used_credit_usd', 0))} / {fmt_usd(c.get('credit_limit_usd', 0))}\n"
                    text += f"   Disp: {fmt_usd(avail_usd)}\n"

        text += "\n━━━━━━━━━━━━━━━━━━━━"

        context.user_data["current_bank_id"] = bank_id
        keyboard = [
            [InlineKeyboardButton("🛒 Registrar Gasto", callback_data=f"action_expense_{bank_id}")],
            [InlineKeyboardButton("📥 Registrar Ingreso", callback_data=f"action_income_{bank_id}")],
            [InlineKeyboardButton("💳 Pagar Tarjeta", callback_data=f"action_pay_{bank_id}")],
            [InlineKeyboardButton("📜 Historial", callback_data=f"action_history_{bank_id}")],
            [InlineKeyboardButton("💸 Transferir", callback_data=f"action_transfer_{bank_id}")],
            [InlineKeyboardButton("◀️ Volver a Bancos", callback_data="menu_banks")],
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

    text = f"📜 *{bank['name']} - ULTIMOS MOVIMIENTOS*\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"

    if not txns:
        text += "No hay movimientos recientes."
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Volver", callback_data=f"bank_{bank_id}")]
            ]),
            parse_mode="Markdown",
        )
        return

    for t in txns:
        icon = "📤" if t["type"] == "gasto" else "📥"
        sign = "-" if t["type"] == "gasto" else "+"
        date = t["created_at"][:10]
        merchant = t.get("merchant") or t.get("category") or "Movimiento"
        currency = t.get("currency", "CLP")
        if currency == "USD":
            amount_str = f"${float(t['amount']):.2f} USD"
        else:
            amount_str = fmt(t["amount"])
        text += f"{icon} {sign}{amount_str} - {merchant}\n"
        text += f"    📅 {date}\n\n"

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
        bank_name = "Banco"
        for b in context.user_data.get("banks", {}).values():
            if b["id"] == a["bank_id"]:
                bank_name = b["name"]
                break
        keyboard.append([
            InlineKeyboardButton(
                f"{bank_name} - {a['name']}: {fmt(a['balance'])}",
                callback_data=f"tsrc_{a['id']}",
            )
        ])
    keyboard.append([InlineKeyboardButton("◀️ Cancelar", callback_data="menu_main")])

    await query.edit_message_text(
        "💸 *TRANSFERIR*\n\nElige la cuenta de origen:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def start_transfer_from_bank(query, context, bank_id):
    await start_transfer(query, context)


async def transfer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    try:
        if data.startswith("tsrc_"):
            src_id = data.replace("tsrc_", "")
            context.user_data["transfer_src"] = src_id
            accounts = context.user_data.get("all_accounts", {})
            keyboard = []
            for aid, a in accounts.items():
                if aid == src_id:
                    continue
                bank_name = "Banco"
                for b in context.user_data.get("banks", {}).values():
                    if b["id"] == a["bank_id"]:
                        bank_name = b["name"]
                        break
                keyboard.append([
                    InlineKeyboardButton(
                        f"{bank_name} - {a['name']}: {fmt(a['balance'])}",
                        callback_data=f"tdst_{aid}",
                    )
                ])
            keyboard.append([InlineKeyboardButton("◀️ Cancelar", callback_data="menu_main")])

            await query.edit_message_text(
                "💸 *TRANSFERIR*\n\nElige la cuenta de destino:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        elif data.startswith("tdst_"):
            dst_id = data.replace("tdst_", "")
            context.user_data["transfer_dst"] = dst_id
            await query.edit_message_text(
                "💸 *TRANSFERIR*\n\nEscribe el monto (solo numeros):",
                parse_mode="Markdown",
            )
            context.user_data["awaiting_transfer_amount"] = True

        elif data == "confirm_transfer":
            await execute_transfer(query, context)

        elif data == "cancel_transfer":
            await show_main_menu(query, context)
    except Exception as e:
        print(f"ERROR in transfer_callback: {e}", flush=True)
        try:
            await query.edit_message_text("Error. Intenta con /start")
        except Exception:
            pass


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

    text = "✅ *TRANSFERENCIA REALIZADA*\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"📤 *Origen:* {src['name']}\n"
    text += f"   Saldo: {fmt(src['balance'])}\n\n"
    text += f"📥 *Destino:* {dst['name']}\n"
    text += f"   Saldo: {fmt(dst['balance'])}\n\n"
    text += f"💵 *Monto:* {fmt(amount)}"

    await query.edit_message_text(
        text,
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
    cards = bd.get("credit_cards", [])
    cards_with_debt = [c for c in cards if float(c["used_credit"]) > 0 or float(c.get("used_credit_usd", 0)) > 0]

    if not cards_with_debt:
        await query.edit_message_text(
            "💳 *PAGAR TARJETA*\n\nNo hay tarjetas con deuda.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Volver", callback_data=f"bank_{bank_id}")]
            ]),
            parse_mode="Markdown",
        )
        return

    context.user_data["pay_cards"] = {c["id"]: c for c in cards_with_debt}
    context.user_data["pay_bank_id"] = bank_id

    text = "💳 *PAGAR TARJETA*\n\nElige la tarjeta a pagar:\n\n"
    keyboard = []
    for c in cards_with_debt:
        parts = []
        if float(c["used_credit"]) > 0:
            parts.append(f"CLP: {fmt(c['used_credit'])}")
        if float(c.get("used_credit_usd", 0)) > 0:
            parts.append(f"USD: {fmt_usd(c.get('used_credit_usd', 0))}")
        text += f"• {c['name']}: {' | '.join(parts)}\n"
        keyboard.append([
            InlineKeyboardButton(
                f"💳 {c['name']}",
                callback_data=f"paycard_{c['id']}",
            )
        ])
    keyboard.append([InlineKeyboardButton("◀️ Volver", callback_data=f"bank_{bank_id}")])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def pay_card_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    try:
        if data.startswith("paycard_"):
            card_id = data.replace("paycard_", "")
            card = context.user_data.get("pay_cards", {}).get(card_id)
            context.user_data["pay_card"] = card

            accounts = await api_get("/api/accounts/all")
            context.user_data["pay_accounts"] = {a["id"]: a for a in accounts}

            text = f"💳 *PAGAR {card['name'].upper()}*\n\n"
            if float(card["used_credit"]) > 0:
                text += f"Deuda CLP: {fmt(card['used_credit'])}\n"
            if float(card.get("used_credit_usd", 0)) > 0:
                text += f"Deuda USD: {fmt_usd(card.get('used_credit_usd', 0))}\n"
            text += "\nElige la cuenta para pagar:\n"

            keyboard = []
            for a in accounts:
                bank_name = "Banco"
                for b in context.user_data.get("banks", {}).values():
                    if b["id"] == a["bank_id"]:
                        bank_name = b["name"]
                        break
                keyboard.append([
                    InlineKeyboardButton(
                        f"{bank_name} - {a['name']}: {fmt(a['balance'])}",
                        callback_data=f"paysrc_{a['id']}",
                    )
                ])
            bank_id = context.user_data.get("pay_bank_id")
            keyboard.append([InlineKeyboardButton("◀️ Volver", callback_data=f"bank_{bank_id}")])

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        elif data.startswith("paysrc_"):
            account_id = data.replace("paysrc_", "")
            context.user_data["pay_src_account"] = account_id
            card = context.user_data.get("pay_card")

            keyboard = [
                [InlineKeyboardButton(
                    f"Pagar total: {fmt(card['used_credit'])}",
                    callback_data="payamt_total",
                )],
                [InlineKeyboardButton(
                    "Pago parcial",
                    callback_data="payamt_partial",
                )],
            ]
            await query.edit_message_text(
                f"💳 *PAGAR {card['name'].upper()}*\n\n"
                f"Deuda: {fmt(card['used_credit'])}\n\n"
                f"Cuanto quieres pagar?",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        elif data == "payamt_total":
            card = context.user_data.get("pay_card")
            context.user_data["pay_amount"] = float(card["used_credit"])
            await confirm_pay(query, context)

        elif data == "payamt_partial":
            await query.edit_message_text(
                "Escribe el monto a pagar (solo numeros):",
                parse_mode="Markdown",
            )
            context.user_data["awaiting_pay_amount"] = True

        elif data == "confirm_pay":
            await execute_pay(query, context)

        elif data == "cancel_pay":
            bank_id = context.user_data.get("pay_bank_id")
            await show_bank_detail(query, context, f"bank_{bank_id}")
    except Exception as e:
        print(f"ERROR in pay_card_callback: {e}", flush=True)
        try:
            await query.edit_message_text("Error. Intenta con /start")
        except Exception:
            pass


async def confirm_pay(query, context):
    card = context.user_data.get("pay_card")
    amount = context.user_data.get("pay_amount")
    accounts = context.user_data.get("pay_accounts", {})
    src_account = accounts.get(context.user_data.get("pay_src_account"), {})

    keyboard = [
        [InlineKeyboardButton("✅ Confirmar pago", callback_data="confirm_pay")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_pay")],
    ]

    new_debt = float(card["used_credit"]) - amount

    text = "💳 *CONFIRMAR PAGO*\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"Tarjeta: *{card['name']}*\n"
    text += f"Cuenta: {src_account.get('name', 'N/A')}\n"
    text += f"Monto: *{fmt(amount)}*\n"
    text += f"Deuda restante: {fmt(max(0, new_debt))}"

    await query.edit_message_text(
        text,
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
            "❌ *Saldo insuficiente en la cuenta.*",
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
        "description": "Pago de tarjeta via Telegram",
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
    p = pct(new_used, card["credit_limit"])

    text = "✅ *PAGO REALIZADO*\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"💳 {card['name']}\n"
    text += f"Deuda: {fmt(new_used)} / {fmt(card['credit_limit'])}\n"
    text += f"{bar(p)} {p:.0f}%\n"
    text += f"{status_emoji(p)} {status_text(p)}"

    await query.edit_message_text(
        text,
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
            "📥 *REGISTRAR INGRESO*\n\nNo hay cuentas en este banco.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Volver", callback_data=f"bank_{bank_id}")]
            ]),
            parse_mode="Markdown",
        )
        return

    context.user_data["income_accounts"] = {a["id"]: a for a in accounts}
    context.user_data["income_bank_id"] = bank_id

    text = "📥 *REGISTRAR INGRESO*\n\nElige la cuenta destino:\n\n"
    keyboard = []
    for a in accounts:
        keyboard.append([
            InlineKeyboardButton(
                f"💰 {a['name']}: {fmt(a['balance'])}",
                callback_data=f"incdst_{a['id']}",
            )
        ])
    keyboard.append([InlineKeyboardButton("◀️ Volver", callback_data=f"bank_{bank_id}")])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def income_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    try:
        if data.startswith("incdst_"):
            account_id = data.replace("incdst_", "")
            context.user_data["income_account"] = account_id
            await query.edit_message_text(
                "📥 *REGISTRAR INGRESO*\n\nEscribe el monto (solo numeros):",
                parse_mode="Markdown",
            )
            context.user_data["awaiting_income_amount"] = True

        elif data == "confirm_income":
            await execute_income(query, context)

        elif data == "cancel_income":
            bank_id = context.user_data.get("income_bank_id")
            await show_bank_detail(query, context, f"bank_{bank_id}")
    except Exception as e:
        print(f"ERROR in income_callback: {e}", flush=True)
        try:
            await query.edit_message_text("Error. Intenta con /start")
        except Exception:
            pass


async def confirm_income_msg(target, context):
    amount = context.user_data.get("income_amount")
    account_id = context.user_data.get("income_account")
    accounts = context.user_data.get("income_accounts", {})
    account = accounts.get(account_id, {})

    keyboard = [
        [InlineKeyboardButton("✅ Confirmar", callback_data="confirm_income")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_income")],
    ]

    new_balance = float(account.get("balance", 0)) + amount

    text = "📥 *CONFIRMAR INGRESO*\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"Cuenta: *{account.get('name', 'N/A')}*\n"
    text += f"Monto: *{fmt(amount)}*\n"
    text += f"Saldo nuevo: {fmt(new_balance)}"

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

    text = "✅ *INGRESO REGISTRADO*\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"💰 {account['name']}: *{fmt(new_balance)}*\n"
    text += f"💵 Ingreso: {fmt(amount)}"

    await query.edit_message_text(
        text,
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
            "🛒 *REGISTRAR GASTO*\n\nNo hay cuentas ni tarjetas en este banco.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Volver", callback_data=f"bank_{bank_id}")]
            ]),
            parse_mode="Markdown",
        )
        return

    context.user_data["expense_bank_id"] = bank_id
    context.user_data["expense_cards"] = {c["id"]: c for c in cards}
    context.user_data["expense_accounts"] = {a["id"]: a for a in accounts}

    text = "🛒 *REGISTRAR GASTO*\n\nElige de donde sale el dinero:\n\n"
    keyboard = []

    if cards:
        text += "💳 *Tarjetas de credito:*\n"
        for c in cards:
            avail_clp = float(c["credit_limit"]) - float(c["used_credit"])
            parts = []
            if float(c["credit_limit"]) > 0:
                parts.append(f"CLP: {fmt(avail_clp)} disp.")
            if float(c.get("credit_limit_usd", 0)) > 0:
                avail_usd = float(c.get("credit_limit_usd", 0)) - float(c.get("used_credit_usd", 0))
                parts.append(f"USD: {fmt_usd(avail_usd)} disp.")
            text += f"   • {c['name']}: {' | '.join(parts)}\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"💳 {c['name']}",
                    callback_data=f"expcard_{c['id']}",
                )
            ])

    if accounts:
        text += "\n💰 *Cuentas de debito:*\n"
        for a in accounts:
            text += f"   • {a['name']}: {fmt(a['balance'])}\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"💰 {a['name']}: {fmt(a['balance'])}",
                    callback_data=f"expacc_{a['id']}",
                )
            ])

    keyboard.append([InlineKeyboardButton("◀️ Volver", callback_data=f"bank_{bank_id}")])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def expense_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    try:
        if data.startswith("expcard_"):
            card_id = data.replace("expcard_", "")
            card = context.user_data.get("expense_cards", {}).get(card_id)
            if not card:
                await query.edit_message_text("Tarjeta no encontrada. Intenta con /start")
                return
            context.user_data["expense_card"] = card
            context.user_data["expense_type"] = "credit_card"

            p_clp = pct(card["used_credit"], card["credit_limit"])
            avail_clp = float(card["credit_limit"]) - float(card["used_credit"])

            text = f"💳 *{card['name']}* - Credito\n\n"
            if float(card["credit_limit"]) > 0:
                text += f"🇨🇱 CLP {bar(p_clp)} {p_clp:.0f}%\n"
                text += f"   Deuda: {fmt(card['used_credit'])} / {fmt(card['credit_limit'])}\n"
                text += f"   Disp: {fmt(avail_clp)}\n\n"

            if float(card.get("credit_limit_usd", 0)) > 0:
                p_usd = pct(card.get("used_credit_usd", 0), card.get("credit_limit_usd", 0))
                avail_usd = float(card.get("credit_limit_usd", 0)) - float(card.get("used_credit_usd", 0))
                text += f"🇺🇸 USD {bar(p_usd)} {p_usd:.0f}%\n"
                text += f"   Deuda: {fmt_usd(card.get('used_credit_usd', 0))} / {fmt_usd(card.get('credit_limit_usd', 0))}\n"
                text += f"   Disp: {fmt_usd(avail_usd)}\n\n"

            text += "Escribe el monto del gasto (solo numeros):"

            await query.edit_message_text(text, parse_mode="Markdown")
            context.user_data["awaiting_expense_amount"] = True

        elif data.startswith("expacc_"):
            account_id = data.replace("expacc_", "")
            account = context.user_data.get("expense_accounts", {}).get(account_id)
            if not account:
                await query.edit_message_text("Cuenta no encontrada. Intenta con /start")
                return
            context.user_data["expense_card"] = account
            context.user_data["expense_type"] = "account"

            await query.edit_message_text(
                f"💰 *{account['name']}* - Debito\n\n"
                f"Saldo: *{fmt(account['balance'])}*\n\n"
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
            new_pct = pct(new_used, limit)
            available = limit - new_used

            text = "✅ *GASTO REGISTRADO*\n"
            text += "━━━━━━━━━━━━━━━━━━━━\n\n"
            text += f"💳 {item['name']}\n"
            text += f"📝 {desc}\n"
            text += f"💵 Gasto: ${amount:.2f} USD\n\n"
            text += f"🇺🇸 USD {bar(new_pct)} {new_pct:.0f}%\n"
            text += f"Deuda: ${new_used:.2f} / ${limit:.2f}\n"
            text += f"Disp: ${available:.2f}\n"
            text += f"{status_emoji(new_pct)} {status_text(new_pct)}"
        else:
            new_used = float(item.get("used_credit", 0)) + amount
            limit = float(item.get("credit_limit", 0))
            new_pct = pct(new_used, limit)
            available = limit - new_used

            text = "✅ *GASTO REGISTRADO*\n"
            text += "━━━━━━━━━━━━━━━━━━━━\n\n"
            text += f"💳 {item['name']}\n"
            text += f"📝 {desc}\n"
            text += f"💵 Gasto: {fmt(amount)} CLP\n\n"
            text += f"🇨🇱 CLP {bar(new_pct)} {new_pct:.0f}%\n"
            text += f"Deuda: {fmt(new_used)} / {fmt(limit)}\n"
            text += f"Disp: {fmt(available)}\n"
            text += f"{status_emoji(new_pct)} {status_text(new_pct)}"
    else:
        if float(item["balance"]) < amount:
            await query.edit_message_text(
                f"❌ *Saldo insuficiente*\n\n"
                f"💰 {item['name']}: {fmt(item['balance'])}\n"
                f"💵 Gasto: {fmt(amount)}",
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
        text = "✅ *GASTO REGISTRADO*\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n\n"
        text += f"💰 {item['name']}\n"
        text += f"📝 {desc}\n"
        text += f"💵 Gasto: {fmt(amount)}\n"
        text += f"📊 Saldo: *{fmt(new_balance)}*\n\n"
        text += "Descontado de tu cuenta de debito."

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
            "Escribe que compraste (ej: Almuerzo, Bencina):",
            parse_mode="Markdown",
        )
    else:
        await target.edit_message_text(
            "Escribe que compraste (ej: Almuerzo, Bencina):",
            parse_mode="Markdown",
        )
    context.user_data["awaiting_expense_description"] = True


async def currency_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    try:
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
                await query.edit_message_text(
                    f"❌ *Excede el limite*\n\n"
                    f"💳 {item.get('name', 'N/A')}\n"
                    f"💵 Gasto: {amount} {currency}\n"
                    f"📊 Limite: {limit} {currency}",
                    parse_mode="Markdown",
                )
                return

            await query.edit_message_text(
                "Escribe que compraste (ej: Almuerzo, Bencina):",
                parse_mode="Markdown",
            )
            context.user_data["awaiting_expense_description"] = True
    except Exception as e:
        print(f"ERROR in currency_callback: {e}", flush=True)
        try:
            await query.edit_message_text("Error. Intenta con /start")
        except Exception:
            pass


# ─── SUMMARY ───
async def show_summary(query, context):
    try:
        banks = await api_get("/api/banks")
    except Exception:
        await query.edit_message_text("Error al cargar datos.")
        return

    text = "📊 *RESUMEN DE CREDITO*\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"

    total_clp_used = 0
    total_clp_limit = 0
    total_usd_used = 0
    total_usd_limit = 0
    has_cards = False

    for b in banks:
        bd = await api_get(f"/api/banks/{b['id']}/data")
        for c in bd.get("credit_cards", []):
            has_cards = True
            used_clp = float(c["used_credit"])
            limit_clp = float(c["credit_limit"])
            used_usd = float(c.get("used_credit_usd", 0))
            limit_usd = float(c.get("credit_limit_usd", 0))

            total_clp_used += used_clp
            total_clp_limit += limit_clp
            total_usd_used += used_usd
            total_usd_limit += limit_usd

            text += f"💳 *{b['name']}* - {c['name']}\n"

            if limit_clp > 0:
                p = pct(used_clp, limit_clp)
                text += f"   🇨🇱 CLP {bar(p)} {p:.0f}%\n"
                text += f"   {fmt(used_clp)} / {fmt(limit_clp)}\n"

            if limit_usd > 0:
                p = pct(used_usd, limit_usd)
                text += f"   🇺🇸 USD {bar(p)} {p:.0f}%\n"
                text += f"   {fmt_usd(used_usd)} / {fmt_usd(limit_usd)}\n"

            text += "\n"

    if not has_cards:
        text += "No hay tarjetas de credito registradas.\n"

    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += "*TOTALES*\n\n"

    if total_clp_limit > 0:
        p = pct(total_clp_used, total_clp_limit)
        text += f"🇨🇱 *CLP*\n"
        text += f"   {bar(p)} {p:.0f}%\n"
        text += f"   {fmt(total_clp_used)} / {fmt(total_clp_limit)}\n"
        text += f"   {status_emoji(p)} {status_text(p)}\n\n"

    if total_usd_limit > 0:
        p = pct(total_usd_used, total_usd_limit)
        text += f"🇺🇸 *USD*\n"
        text += f"   {bar(p)} {p:.0f}%\n"
        text += f"   {fmt_usd(total_usd_used)} / {fmt_usd(total_usd_limit)}\n"
        text += f"   {status_emoji(p)} {status_text(p)}\n"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Menu principal", callback_data="menu_main")]
        ]),
        parse_mode="Markdown",
    )


# ─── HELP ───
async def show_help(query):
    text = "❓ *AYUDA*\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    text += "🏦 *Mis Bancos* - Ver cuentas y tarjetas por banco\n"
    text += "📊 *Resumen Credito* - Uso global CLP y USD\n"
    text += "💸 *Transferir* - Mover dinero entre cuentas\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += "*Dentro de cada banco:*\n\n"
    text += "🛒 *Registrar Gasto* - Uso de tarjeta o debito\n"
    text += "📥 *Registrar Ingreso* - Agregar dinero\n"
    text += "💳 *Pagar Tarjeta* - Pagar deuda con una cuenta\n"
    text += "📜 *Historial* - Ultimos movimientos\n"
    text += "💸 *Transferir* - Mover dinero\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += "*Objetivo crediticio:*\n"
    text += "Usa entre 20-30% de tu credito\n"
    text += "para mejorar tu historial.\n\n"
    text += "🟢 Bajo 20% - Vas bien\n"
    text += "🟡 20-30% - Rango ideal\n"
    text += "🔴 Mas del 30% - ALERTA"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Menu principal", callback_data="menu_main")]
        ]),
        parse_mode="Markdown",
    )


# ─── TEXT HANDLER ───
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

        text = "💸 *CONFIRMAR TRANSFERENCIA*\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n\n"
        text += f"📤 *Origen:* {src.get('name', 'N/A')}\n"
        text += f"   Saldo: {fmt(float(src.get('balance', 0)))}\n\n"
        text += f"📥 *Destino:* {dst.get('name', 'N/A')}\n"
        text += f"   Saldo: {fmt(float(dst.get('balance', 0)))}\n\n"
        text += f"💵 *Monto:* {fmt(amount)}\n\n"
        text += f"Origen despues: {fmt(float(src.get('balance', 0)) - amount)}\n"
        text += f"Destino despues: {fmt(float(dst.get('balance', 0)) + amount)}"

        await update.message.reply_text(
            text,
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
        await confirm_pay(update.message, context)

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
            await update.message.reply_text("Error al procesar. Intenta con /start")

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
                        "En que moneda quieres el gasto?",
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
                        f"❌ *Saldo insuficiente*\n\n"
                        f"💰 {item.get('name', 'N/A')}: {fmt(balance)}\n"
                        f"💵 Gasto: {fmt(amount)}",
                        parse_mode="Markdown",
                    )
                    return
                await ask_expense_description(update.message, context)
        except Exception as e:
            print(f"ERROR in expense flow: {e}", flush=True)
            await update.message.reply_text("Error al procesar. Intenta con /start")

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
                    new_pct = pct(new_used, limit)

                    keyboard = [
                        [InlineKeyboardButton("✅ Confirmar gasto", callback_data="exec_expense")],
                        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_expense")],
                    ]

                    text = "🛒 *CONFIRMAR GASTO*\n"
                    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
                    text += f"💳 {item.get('name', 'N/A')} (Credito)\n"
                    text += f"📝 {desc}\n"
                    text += f"💵 Monto: ${amount:.2f} USD\n\n"
                    text += f"🇺🇸 USD {bar(new_pct)} {new_pct:.0f}%\n"
                    text += f"Deuda nueva: ${new_used:.2f} / ${limit:.2f}\n"
                    text += f"{status_emoji(new_pct)} {status_text(new_pct)}"

                    await update.message.reply_text(
                        text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="Markdown",
                    )
                else:
                    new_used = float(item.get("used_credit", 0)) + amount
                    limit = float(item.get("credit_limit", 0))
                    new_pct = pct(new_used, limit)

                    keyboard = [
                        [InlineKeyboardButton("✅ Confirmar gasto", callback_data="exec_expense")],
                        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_expense")],
                    ]

                    text = "🛒 *CONFIRMAR GASTO*\n"
                    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
                    text += f"💳 {item.get('name', 'N/A')} (Credito)\n"
                    text += f"📝 {desc}\n"
                    text += f"💵 Monto: {fmt(amount)} CLP\n\n"
                    text += f"🇨🇱 CLP {bar(new_pct)} {new_pct:.0f}%\n"
                    text += f"Deuda nueva: {fmt(new_used)} / {fmt(limit)}\n"
                    text += f"{status_emoji(new_pct)} {status_text(new_pct)}"

                    await update.message.reply_text(
                        text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="Markdown",
                    )
            else:
                new_balance = float(item.get("balance", 0)) - amount

                keyboard = [
                    [InlineKeyboardButton("✅ Confirmar gasto", callback_data="exec_expense")],
                    [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_expense")],
                ]

                text = "🛒 *CONFIRMAR GASTO*\n"
                text += "━━━━━━━━━━━━━━━━━━━━\n\n"
                text += f"💰 {item.get('name', 'N/A')} (Debito)\n"
                text += f"📝 {desc}\n"
                text += f"💵 Monto: {fmt(amount)}\n"
                text += f"📊 Saldo nuevo: *{fmt(new_balance)}*"

                await update.message.reply_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown",
                )
        except Exception as e:
            print(f"ERROR in expense confirm: {e}", flush=True)
            await update.message.reply_text("Error al procesar. Intenta con /start")


# ─── MAIN ───
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import traceback
    print(f"BOT ERROR: {context.error}", flush=True)
    print(f"TRACEBACK: {traceback.format_exc()}", flush=True)
    if update and update.callback_query:
        print(f"CALLBACK DATA: {update.callback_query.data}", flush=True)
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
