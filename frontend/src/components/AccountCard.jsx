import { useState, useEffect } from "react";
import { deleteAccount, applyInterest } from "../api/banks";
import EditAccountModal from "./EditAccountModal";

function getGradient(color) {
  return `linear-gradient(135deg, ${color}, ${color}dd)`;
}

function getTextColor(hex) {
  if (!hex) return "#ffffff";
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.5 ? "#000000" : "#ffffff";
}

export default function AccountCard({ account, bankName, bankLogo, onRefresh }) {
  const [showEdit, setShowEdit] = useState(false);

  useEffect(() => {
    if (account.interest_rate > 0 && !account.is_uf_indexed && !account.last_interest_date) {
      applyInterest(account.id).then(() => onRefresh()).catch(console.error);
    }
  }, [account.id]);

  async function handleDelete(e) {
    e.stopPropagation();
    if (!confirm("Eliminar esta cuenta?")) return;
    await deleteAccount(account.id);
    onRefresh();
  }

  const formattedBalance = new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "CLP",
    maximumFractionDigits: 0,
  }).format(account.balance);

  const hasInterest = account.interest_rate > 0;
  const dailyRate = hasInterest ? ((Math.pow(1 + account.interest_rate / 100, 1 / 365) - 1) * 100).toFixed(4) : 0;
  const monthlyRate = hasInterest ? ((Math.pow(1 + account.interest_rate / 100, 1 / 12) - 1) * 100).toFixed(2) : 0;
  const textColor = getTextColor(account.color);

  const daysToMaturity = account.maturity_date
    ? Math.ceil((new Date(account.maturity_date) - new Date()) / (1000 * 60 * 60 * 24))
    : null;
  const maturityDate = account.maturity_date
    ? new Date(account.maturity_date).toLocaleDateString("es-CL")
    : null;
  const remainingWithdrawals = account.max_free_withdrawals - (account.withdrawals_this_year || 0);

  return (
    <>
      <div className="relative group">
        <div
          className="w-72 h-48 rounded-2xl p-5 flex flex-col justify-between shadow-xl"
          style={{ background: getGradient(account.color || "#1a1d2e"), color: textColor }}
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
            <span className="text-[10px] font-bold tracking-wider opacity-80">
              {account.is_uf_indexed ? "Ahorro Premium" : "DEBIT"}
            </span>
          </div>
          <div>
            <p className="text-2xl font-bold tracking-tight">{formattedBalance}</p>
            <p className="text-[10px] opacity-60 uppercase tracking-wide mt-1">{account.name}</p>
            {account.is_uf_indexed ? (
              <p className="text-[10px] opacity-50">UF · Reajustable por inflación</p>
            ) : (
              <p className="text-[10px] opacity-40">
                **** **** **** {account.card_number || "0000"}
              </p>
            )}
          </div>
        </div>
        {account.is_uf_indexed && (
          <div className="mt-2 space-y-1">
            <div className="flex items-center gap-2 text-[10px]">
              <span className="px-1.5 py-0.5 rounded bg-green-500/20 text-green-400 font-medium">
                +{account.interest_rate}% anual
              </span>
              <span className="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 font-medium">
                {remainingWithdrawals} giros gratis restantes
              </span>
            </div>
            {maturityDate && (
              <div className="flex items-center gap-1 text-[10px] text-gray-500">
                <span>Vence: {maturityDate}</span>
                {daysToMaturity > 0 && <span>({daysToMaturity} días)</span>}
              </div>
            )}
            <div className="flex items-center gap-2 text-[10px] text-gray-500">
              <span>{dailyRate}% diario</span>
              <span>·</span>
              <span>{monthlyRate}% mensual</span>
            </div>
          </div>
        )}
        {!account.is_uf_indexed && hasInterest && (
          <div className="mt-2 space-y-0.5">
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-500/20 text-green-400 font-medium">
              +{account.interest_rate}% anual
            </span>
            <div className="flex items-center gap-2 text-[10px] text-gray-500">
              <span>{dailyRate}% diario</span>
              <span>·</span>
              <span>{monthlyRate}% mensual</span>
            </div>
          </div>
        )}
        <div className="absolute top-3 right-3 flex gap-1 opacity-0 group-hover:opacity-100 transition-all">
          <button
            onClick={(e) => { e.stopPropagation(); setShowEdit(true); }}
            className="text-gray-400 hover:text-blue-400 text-xs p-1 cursor-pointer"
            title="Editar cuenta"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </button>
          <button
            onClick={handleDelete}
            className="text-gray-400 hover:text-red-400 text-xs p-1 cursor-pointer"
            title="Eliminar cuenta"
          >
            x
          </button>
        </div>
      </div>

      {showEdit && (
        <EditAccountModal
          account={account}
          onClose={() => setShowEdit(false)}
          onUpdated={() => { setShowEdit(false); onRefresh(); }}
        />
      )}
    </>
  );
}
