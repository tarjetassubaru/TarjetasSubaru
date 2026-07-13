import { useState } from "react";
import { deleteCreditCard } from "../api/banks";
import EditCreditCardModal from "./EditCreditCardModal";

function getGradient(color) {
  return `linear-gradient(135deg, ${color}, ${color}cc)`;
}

function getTextColor(hex) {
  if (!hex) return "#ffffff";
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.5 ? "#000000" : "#ffffff";
}

export default function CreditCardVisual({ card, bankName, bankLogo, onRefresh }) {
  const [showEdit, setShowEdit] = useState(false);

  async function handleDelete(e) {
    e.stopPropagation();
    if (!confirm("Eliminar esta tarjeta?")) return;
    await deleteCreditCard(card.id);
    onRefresh();
  }

  const available = card.credit_limit - card.used_credit;
  const percentage = card.credit_limit > 0 ? Math.min((card.used_credit / card.credit_limit) * 100, 100) : 0;

  const hasUSD = (card.credit_limit_usd || 0) > 0;
  const availableUSD = (card.credit_limit_usd || 0) - (card.used_credit_usd || 0);
  const percentageUSD = hasUSD ? Math.min(((card.used_credit_usd || 0) / card.credit_limit_usd) * 100, 100) : 0;

  const formattedLimit = new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "CLP",
    maximumFractionDigits: 0,
  }).format(card.credit_limit);

  const formattedAvailable = new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "CLP",
    maximumFractionDigits: 0,
  }).format(available);

  const formattedUsed = new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "CLP",
    maximumFractionDigits: 0,
  }).format(card.used_credit);

  const franchiseLabel = { visa: "VISA", mastercard: "MASTERCARD", amex: "AMEX" };
  const textColor = getTextColor(card.color);

  return (
    <>
      <div className="relative group">
        <div
          className="w-72 h-48 rounded-2xl p-5 flex flex-col justify-between shadow-xl"
          style={{ background: getGradient(card.color || "#1a1d2e"), color: textColor }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {bankLogo ? (
                <img src={bankLogo} alt={bankName} className="w-6 h-6 object-contain" />
              ) : (
                <span className="text-xs font-bold opacity-80">{bankName?.charAt(0)}</span>
              )}
              <span className="text-xs opacity-80">{bankName}</span>
            </div>
            <span className="text-[10px] font-bold tracking-wider opacity-80">CREDIT</span>
          </div>
          <div>
            <p className="text-2xl font-bold tracking-tight">{formattedAvailable}</p>
            <p className="text-[10px] opacity-60 uppercase tracking-wide mt-1">{card.name}</p>
            <div className="flex items-center justify-between">
              <p className="text-[10px] opacity-40">
                **** **** **** {card.card_number || "0000"}
              </p>
              <p className="text-[10px] opacity-40">{franchiseLabel[card.franchise] || card.franchise?.toUpperCase()}</p>
            </div>
          </div>
        </div>
        <div className="mt-2 space-y-1">
          <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${percentage}%`,
                background: percentage > 80 ? "#ef4444" : percentage > 50 ? "#f59e0b" : "#22c55e",
              }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-gray-500">
            <span>{formattedUsed} usado de {formattedLimit}</span>
            <span>{percentage.toFixed(0)}%</span>
          </div>
          <div className="flex justify-between text-[10px] text-gray-600">
            <span>Cierre dia {card.closing_day}</span>
            <span>Pago dia {card.payment_day}</span>
          </div>
          {hasUSD && (
            <>
              <div className="mt-2 pt-2 border-t border-white/10">
                <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${percentageUSD}%`,
                      background: percentageUSD > 80 ? "#ef4444" : percentageUSD > 50 ? "#f59e0b" : "#3b82f6",
                    }}
                  />
                </div>
                <div className="flex justify-between text-[10px] text-gray-500 mt-1">
                  <span>${(card.used_credit_usd || 0).toFixed(2)} usado de ${(card.credit_limit_usd || 0).toFixed(2)} USD</span>
                  <span>{percentageUSD.toFixed(0)}%</span>
                </div>
              </div>
            </>
          )}
        </div>
        <div className="absolute top-3 right-3 flex gap-1 opacity-0 group-hover:opacity-100 transition-all">
          <button
            onClick={(e) => { e.stopPropagation(); setShowEdit(true); }}
            className="text-gray-400 hover:text-blue-400 text-xs p-1 cursor-pointer"
            title="Editar tarjeta"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </button>
          <button
            onClick={handleDelete}
            className="text-gray-400 hover:text-red-400 text-xs p-1 cursor-pointer"
            title="Eliminar tarjeta"
          >
            x
          </button>
        </div>
      </div>

      {showEdit && (
        <EditCreditCardModal
          card={card}
          onClose={() => setShowEdit(false)}
          onUpdated={() => { setShowEdit(false); onRefresh(); }}
        />
      )}
    </>
  );
}
