import { useState } from "react";
import { updateCreditCard } from "../api/banks";

const COLORS = ["#ffffff", "#ec0000", "#333333", "#0a4c8a", "#cc1e25", "#ff2318", "#004dff", "#aad63e", "#bd2426", "#ffe600", "#009ee3"];

const FRANCHISES = [
  { value: "visa", label: "Visa" },
  { value: "mastercard", label: "Mastercard" },
  { value: "amex", label: "American Express" },
];

export default function EditCreditCardModal({ card, onClose, onUpdated }) {
  const [name, setName] = useState(card.name);
  const [franchise, setFranchise] = useState(card.franchise);
  const [creditLimit, setCreditLimit] = useState(String(card.credit_limit));
  const [usedCredit, setUsedCredit] = useState(String(card.used_credit));
  const [closingDay, setClosingDay] = useState(String(card.closing_day));
  const [paymentDay, setPaymentDay] = useState(String(card.payment_day));
  const [cardNumber, setCardNumber] = useState(card.card_number || "");
  const [color, setColor] = useState(card.color || "#1a1d2e");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError("");
    try {
      await updateCreditCard(card.id, {
        name: name.trim(),
        franchise,
        credit_limit: parseFloat(creditLimit) || 0,
        used_credit: parseFloat(usedCredit) || 0,
        closing_day: parseInt(closingDay),
        payment_day: parseInt(paymentDay),
        card_number: cardNumber.trim() || null,
        color,
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
        <h3 className="text-lg font-semibold text-gray-200 mb-4">Editar Tarjeta de Credito</h3>
        <form onSubmit={handleSubmit}>
          <label className="block mb-1 text-sm text-gray-400">Nombre</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
            className="w-full px-3 py-2.5 bg-[#1a1d2e] border border-gray-700 rounded-lg text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-gray-500 transition-colors mb-3"
          />

          <label className="block mb-1 text-sm text-gray-400">Franquicia</label>
          <select
            value={franchise}
            onChange={(e) => setFranchise(e.target.value)}
            className="w-full px-3 py-2.5 bg-[#1a1d2e] border border-gray-700 rounded-lg text-gray-200 text-sm focus:outline-none focus:border-gray-500 transition-colors mb-3"
          >
            {FRANCHISES.map((f) => (
              <option key={f.value} value={f.value}>{f.label}</option>
            ))}
          </select>

          <label className="block mb-1 text-sm text-gray-400">Cupo total</label>
          <input
            type="number"
            value={creditLimit}
            onChange={(e) => setCreditLimit(e.target.value)}
            className="w-full px-3 py-2.5 bg-[#1a1d2e] border border-gray-700 rounded-lg text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-gray-500 transition-colors mb-3"
          />

          <label className="block mb-1 text-sm text-gray-400">Cupo utilizado</label>
          <input
            type="number"
            value={usedCredit}
            onChange={(e) => setUsedCredit(e.target.value)}
            className="w-full px-3 py-2.5 bg-[#1a1d2e] border border-gray-700 rounded-lg text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-gray-500 transition-colors mb-3"
          />

          <div className="flex gap-3 mb-3">
            <div className="flex-1">
              <label className="block mb-1 text-sm text-gray-400">Dia cierre</label>
              <input
                type="number"
                value={closingDay}
                onChange={(e) => setClosingDay(e.target.value)}
                min="1"
                max="31"
                className="w-full px-3 py-2.5 bg-[#1a1d2e] border border-gray-700 rounded-lg text-gray-200 text-sm focus:outline-none focus:border-gray-500 transition-colors"
              />
            </div>
            <div className="flex-1">
              <label className="block mb-1 text-sm text-gray-400">Dia pago</label>
              <input
                type="number"
                value={paymentDay}
                onChange={(e) => setPaymentDay(e.target.value)}
                min="1"
                max="31"
                className="w-full px-3 py-2.5 bg-[#1a1d2e] border border-gray-700 rounded-lg text-gray-200 text-sm focus:outline-none focus:border-gray-500 transition-colors"
              />
            </div>
          </div>

          <label className="block mb-1 text-sm text-gray-400">Ultimos 4 digitos</label>
          <input
            type="text"
            value={cardNumber}
            onChange={(e) => setCardNumber(e.target.value.slice(0, 4))}
            placeholder="1234"
            maxLength={4}
            className="w-full px-3 py-2.5 bg-[#1a1d2e] border border-gray-700 rounded-lg text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-gray-500 transition-colors mb-3"
          />

          <label className="block mb-2 text-sm text-gray-400">Color</label>
          <div className="flex gap-2 mb-4">
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
