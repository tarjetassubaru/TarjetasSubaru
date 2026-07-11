function formatDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("es-CL", { day: "2-digit", month: "short", year: "2-digit" });
}

function getMethodName(transaction, accounts, creditCards) {
  if (transaction.account_id) {
    const acc = accounts.find((a) => a.id === transaction.account_id);
    return acc ? `${acc.name}` : "Cuenta eliminada";
  }
  if (transaction.credit_card_id) {
    const card = creditCards.find((c) => c.id === transaction.credit_card_id);
    return card ? `${card.name}` : "Tarjeta eliminada";
  }
  return "-";
}

export default function MovementsTable({ transactions, accounts, creditCards }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-800">
            <th className="text-left py-3 px-3 text-gray-500 font-medium">Fecha</th>
            <th className="text-left py-3 px-3 text-gray-500 font-medium">Tipo</th>
            <th className="text-left py-3 px-3 text-gray-500 font-medium">Comercio</th>
            <th className="text-left py-3 px-3 text-gray-500 font-medium">Categoria</th>
            <th className="text-left py-3 px-3 text-gray-500 font-medium">Metodo</th>
            <th className="text-right py-3 px-3 text-gray-500 font-medium">Monto</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((t) => (
            <tr key={t.id} className="border-b border-gray-800/50 hover:bg-[#1a1d2e]/50">
              <td className="py-3 px-3 text-gray-400">{formatDate(t.created_at)}</td>
              <td className="py-3 px-3">
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  t.type === "gasto"
                    ? "bg-red-500/20 text-red-400"
                    : "bg-green-500/20 text-green-400"
                }`}>
                  {t.type === "gasto" ? "Gasto" : "Ingreso"}
                </span>
              </td>
              <td className="py-3 px-3 text-gray-300">{t.merchant || "-"}</td>
              <td className="py-3 px-3 text-gray-500">{t.category || "-"}</td>
              <td className="py-3 px-3 text-gray-500">{getMethodName(t, accounts, creditCards)}</td>
              <td className={`py-3 px-3 text-right font-medium ${
                t.type === "gasto" ? "text-red-400" : "text-green-400"
              }`}>
                {t.type === "gasto" ? "-" : "+"}${t.amount.toLocaleString("es-CL")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
