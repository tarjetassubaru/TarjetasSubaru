import { useState } from "react";

const CATEGORIES = [
  "Alimentacion",
  "Transporte",
  "Entretenimiento",
  "Salud",
  "Educacion",
  "Servicios",
  "Ropa",
  "Tecnologia",
  "Hogar",
  "Otros",
];

export default function TransactionModal({ paymentMethods, onClose, onSubmit }) {
  const [type, setType] = useState("gasto");
  const [methodIndex, setMethodIndex] = useState("0");
  const [amount, setAmount] = useState("");
  const [merchant, setMerchant] = useState("");
  const [category, setCategory] = useState("Otros");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!amount || parseFloat(amount) <= 0) return;
    setLoading(true);

    const method = paymentMethods[parseInt(methodIndex)];
    const data = {
      type,
      amount: parseFloat(amount),
      merchant: merchant.trim() || null,
      category,
      description: description.trim() || null,
    };

    if (method.type === "account") {
      data.account_id = method.id;
    } else {
      data.credit_card_id = method.id;
    }

    await onSubmit(data);
    setLoading(false);
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-[#0f1117] border border-gray-800 rounded-xl w-full max-w-sm mx-4 p-6 shadow-2xl">
        <h3 className="text-lg font-semibold text-gray-200 mb-4">Registrar Movimiento</h3>
        <form onSubmit={handleSubmit}>
          <div className="flex gap-2 mb-4">
            <button
              type="button"
              onClick={() => setType("gasto")}
              className={`flex-1 py-2 text-sm rounded-lg border transition-colors cursor-pointer ${
                type === "gasto"
                  ? "bg-red-500/20 border-red-500/50 text-red-400"
                  : "bg-[#1a1d2e] border-gray-700 text-gray-400 hover:border-gray-600"
              }`}
            >
              Gasto
            </button>
            <button
              type="button"
              onClick={() => setType("ingreso")}
              className={`flex-1 py-2 text-sm rounded-lg border transition-colors cursor-pointer ${
                type === "ingreso"
                  ? "bg-green-500/20 border-green-500/50 text-green-400"
                  : "bg-[#1a1d2e] border-gray-700 text-gray-400 hover:border-gray-600"
              }`}
            >
              Ingreso
            </button>
          </div>

          {paymentMethods.length > 0 && (
            <>
              <label className="block mb-1 text-sm text-gray-400">Metodo de pago</label>
              <select
                value={methodIndex}
                onChange={(e) => setMethodIndex(e.target.value)}
                className="w-full px-3 py-2.5 bg-[#1a1d2e] border border-gray-700 rounded-lg text-gray-200 text-sm focus:outline-none focus:border-gray-500 transition-colors mb-3"
              >
                {paymentMethods.map((m, i) => (
                  <option key={m.id} value={i}>{m.name}</option>
                ))}
              </select>
            </>
          )}

          <label className="block mb-1 text-sm text-gray-400">Monto</label>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0"
            min="0"
            autoFocus
            className="w-full px-3 py-2.5 bg-[#1a1d2e] border border-gray-700 rounded-lg text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-gray-500 transition-colors mb-3"
          />

          <label className="block mb-1 text-sm text-gray-400">Comercio</label>
          <input
            type="text"
            value={merchant}
            onChange={(e) => setMerchant(e.target.value)}
            placeholder="Ej: Mercado Libre"
            className="w-full px-3 py-2.5 bg-[#1a1d2e] border border-gray-700 rounded-lg text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-gray-500 transition-colors mb-3"
          />

          <label className="block mb-1 text-sm text-gray-400">Categoria</label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full px-3 py-2.5 bg-[#1a1d2e] border border-gray-700 rounded-lg text-gray-200 text-sm focus:outline-none focus:border-gray-500 transition-colors mb-3"
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>

          <label className="block mb-1 text-sm text-gray-400">Descripcion (opcional)</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Nota..."
            rows={2}
            className="w-full px-3 py-2.5 bg-[#1a1d2e] border border-gray-700 rounded-lg text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-gray-500 transition-colors mb-4 resize-none"
          />

          <div className="flex justify-end gap-3">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-gray-300 transition-colors cursor-pointer">
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading || !amount}
              className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-lg disabled:opacity-40 transition-colors cursor-pointer"
            >
              {loading ? "Guardando..." : "Registrar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
