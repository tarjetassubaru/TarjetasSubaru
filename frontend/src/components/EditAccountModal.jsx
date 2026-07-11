import { useState } from "react";
import { updateAccount } from "../api/banks";

const COLORS = ["#ffffff", "#ec0000", "#333333", "#0a4c8a", "#cc1e25", "#ff2318", "#004dff", "#aad63e", "#bd2426", "#ffe600", "#009ee3"];

const ACCOUNT_TYPES = [
  { value: "vista", label: "Vista" },
  { value: "corriente", label: "Corriente" },
  { value: "ahorro", label: "Ahorro" },
  { value: "ahorro_premium", label: "Ahorro Premium (UF)" },
];

export default function EditAccountModal({ account, onClose, onUpdated }) {
  const [name, setName] = useState(account.name);
  const [accountType, setAccountType] = useState(account.account_type);
  const [balance, setBalance] = useState(String(account.balance));
  const [cardNumber, setCardNumber] = useState(account.card_number || "");
  const [color, setColor] = useState(account.color || "#1a1d2e");
  const [interestRate, setInterestRate] = useState(String(account.interest_rate || ""));
  const [isUfIndexed, setIsUfIndexed] = useState(account.is_uf_indexed || false);
  const [depositDate, setDepositDate] = useState(account.deposit_date ? account.deposit_date.split("T")[0] : "");
  const [maturityDate, setMaturityDate] = useState(account.maturity_date ? account.maturity_date.split("T")[0] : "");
  const [withdrawalsThisYear, setWithdrawalsThisYear] = useState(String(account.withdrawals_this_year || 0));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError("");
    try {
      await updateAccount(account.id, {
        name: name.trim(),
        balance: parseFloat(balance) || 0,
        card_number: cardNumber.trim() || null,
        color,
        interest_rate: parseFloat(interestRate) || 0,
        is_uf_indexed: accountType === "ahorro_premium" || isUfIndexed,
        deposit_date: depositDate ? new Date(depositDate).toISOString() : null,
        maturity_date: maturityDate ? new Date(maturityDate).toISOString() : null,
        withdrawals_this_year: parseInt(withdrawalsThisYear) || 0,
      });
      onUpdated();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-[#0f1117] border border-gray-800 rounded-xl w-full max-w-sm mx-4 p-6 shadow-2xl">
        <h3 className="text-lg font-semibold text-gray-200 mb-4">Editar Cuenta</h3>
        <form onSubmit={handleSubmit}>
          <label className="block mb-1 text-sm text-gray-400">Nombre</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
            className="w-full px-3 py-2.5 bg-[#1a1d2e] border border-gray-700 rounded-lg text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-gray-500 transition-colors mb-3"
          />

          <label className="block mb-1 text-sm text-gray-400">Tipo de cuenta</label>
          <select
            value={accountType}
            onChange={(e) => setAccountType(e.target.value)}
            className="w-full px-3 py-2.5 bg-[#1a1d2e] border border-gray-700 rounded-lg text-gray-200 text-sm focus:outline-none focus:border-gray-500 transition-colors mb-3"
          >
            {ACCOUNT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>

          <label className="block mb-1 text-sm text-gray-400">Saldo</label>
          <input
            type="number"
            value={balance}
            onChange={(e) => setBalance(e.target.value)}
            className="w-full px-3 py-2.5 bg-[#1a1d2e] border border-gray-700 rounded-lg text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-gray-500 transition-colors mb-3"
          />

          <label className="block mb-1 text-sm text-gray-400">Tasa de interes anual (%)</label>
          <input
            type="number"
            value={interestRate}
            onChange={(e) => setInterestRate(e.target.value)}
            step="0.1"
            min="0"
            max="100"
            className="w-full px-3 py-2.5 bg-[#1a1d2e] border border-gray-700 rounded-lg text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-gray-500 transition-colors mb-3"
          />

          {!account.is_uf_indexed && (
            <>
              <label className="block mb-1 text-sm text-gray-400">Ultimos 4 digitos</label>
              <input
                type="text"
                value={cardNumber}
                onChange={(e) => setCardNumber(e.target.value.slice(0, 4))}
                placeholder="1234"
                maxLength={4}
                className="w-full px-3 py-2.5 bg-[#1a1d2e] border border-gray-700 rounded-lg text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-gray-500 transition-colors mb-3"
              />
            </>
          )}

          <label className="block mb-2 text-sm text-gray-400">Color</label>
          <div className="flex gap-2 mb-3">
            {COLORS.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setColor(c)}
                className={`w-7 h-7 rounded-full border-2 transition-colors cursor-pointer ${
                  color === c ? "border-white" : "border-transparent"
                }`}
                style={{ background: c }}
              />
            ))}
          </div>

          {(accountType === "ahorro_premium" || isUfIndexed) && (
            <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg mb-3">
              <p className="text-[10px] text-blue-400 font-medium mb-2">Cuenta Ahorro Premium UF</p>
              <label className="block mb-1 text-xs text-gray-400">Fecha de deposito</label>
              <input
                type="date"
                value={depositDate}
                onChange={(e) => setDepositDate(e.target.value)}
                className="w-full px-3 py-2 bg-[#1a1d2e] border border-gray-700 rounded-lg text-gray-200 text-sm focus:outline-none focus:border-gray-500 transition-colors mb-2"
              />
              <label className="block mb-1 text-xs text-gray-400">Fecha de vencimiento</label>
              <input
                type="date"
                value={maturityDate}
                onChange={(e) => setMaturityDate(e.target.value)}
                className="w-full px-3 py-2 bg-[#1a1d2e] border border-gray-700 rounded-lg text-gray-200 text-sm focus:outline-none focus:border-gray-500 transition-colors mb-2"
              />
              <label className="block mb-1 text-xs text-gray-400">Giros este año</label>
              <input
                type="number"
                value={withdrawalsThisYear}
                onChange={(e) => setWithdrawalsThisYear(e.target.value)}
                min="0"
                max="12"
                className="w-full px-3 py-2 bg-[#1a1d2e] border border-gray-700 rounded-lg text-gray-200 text-sm focus:outline-none focus:border-gray-500 transition-colors mb-1"
              />
              <p className="text-[9px] text-gray-500">Giros gratis restantes: {3 - (parseInt(withdrawalsThisYear) || 0)}</p>
            </div>
          )}

          {error && <p className="text-red-400 text-xs mb-2">{error}</p>}

          <div className="flex justify-end gap-3 mt-4">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-gray-300 transition-colors cursor-pointer">
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="px-4 py-2 text-sm bg-[#1a1d2e] hover:bg-[#252840] border border-gray-700/50 text-gray-200 rounded-lg disabled:opacity-40 transition-colors cursor-pointer"
            >
              {loading ? "Guardando..." : "Guardar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
