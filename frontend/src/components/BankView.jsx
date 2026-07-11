import { useState, useEffect } from "react";
import {
  getBankData,
  createTransaction,
} from "../api/banks";
import AddAccountModal from "./AddAccountModal";
import AddCreditCardModal from "./AddCreditCardModal";
import AccountCard from "./AccountCard";
import CreditCardVisual from "./CreditCardVisual";
import MovementsTable from "./MovementsTable";

export default function BankView({ bank, refreshBanks }) {
  const [accounts, setAccounts] = useState([]);
  const [creditCards, setCreditCards] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAccountModal, setShowAccountModal] = useState(false);
  const [showCreditCardModal, setShowCreditCardModal] = useState(false);
  const [showTransactionModal, setShowTransactionModal] = useState(false);

  const loadAll = () => {
    setLoading(true);
    getBankData(bank.id)
      .then((data) => {
        setAccounts(data.accounts);
        setCreditCards(data.credit_cards);
        setTransactions(data.transactions);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    setAccounts([]);
    setCreditCards([]);
    setTransactions([]);
    loadAll();
  }, [bank.id]);

  const refreshAll = () => {
    getBankData(bank.id)
      .then((data) => {
        setAccounts(data.accounts);
        setCreditCards(data.credit_cards);
        setTransactions(data.transactions);
      })
      .catch(console.error);
    if (refreshBanks) refreshBanks();
  };

  async function handleCreateTransaction(data) {
    await createTransaction({ ...data, bank_id: bank.id });
    setShowTransactionModal(false);
    refreshAll();
  }

  const paymentMethods = [
    ...accounts.map((a) => ({ id: a.id, type: "account", name: `Débito - ${a.name}` })),
    ...creditCards.map((c) => ({ id: c.id, type: "credit_card", name: `Crédito - ${c.name}` })),
  ];

  return (
    <div className="flex-1 p-8 overflow-y-auto">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center overflow-hidden">
            {bank.logo ? (
              <img src={bank.logo} alt={bank.name} className="w-8 h-8 object-contain" />
            ) : (
              <span className="text-lg font-bold text-gray-500">{bank.name.charAt(0)}</span>
            )}
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-200">{bank.name}</h1>
            <p className="text-xs text-gray-500">Panel de cuentas</p>
          </div>
        </div>
        <button
          onClick={() => setShowTransactionModal(true)}
          className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors cursor-pointer"
        >
          + Registrar Movimiento
        </button>
      </div>

      <div className="flex gap-3 mb-6">
        <button
          onClick={() => setShowAccountModal(true)}
          className="px-4 py-2 text-sm bg-[#1a1d2e] hover:bg-[#252840] text-gray-300 border border-gray-700/50 rounded-lg transition-colors cursor-pointer"
        >
          + Cuenta de Débito/Corriente
        </button>
        <button
          onClick={() => setShowCreditCardModal(true)}
          className="px-4 py-2 text-sm bg-[#1a1d2e] hover:bg-[#252840] text-gray-300 border border-gray-700/50 rounded-lg transition-colors cursor-pointer"
        >
          + Tarjeta de Crédito
        </button>
      </div>

      {loading && (
        <div className="flex items-center justify-center h-32">
          <div className="text-gray-500 text-sm">Cargando...</div>
        </div>
      )}

      {!loading && accounts.length === 0 && creditCards.length === 0 && (
        <div className="flex items-center justify-center h-64 border border-dashed border-gray-800 rounded-xl">
          <p className="text-gray-600 text-sm">Agrega una cuenta o tarjeta de credito para comenzar</p>
        </div>
      )}

      {accounts.length > 0 && (
        <div className="mb-6">
          <h2 className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-3">Cuentas</h2>
          <div className="flex flex-wrap gap-4">
            {accounts.map((account) => (
              <AccountCard
                key={account.id}
                account={account}
                bankName={bank.name}
                bankLogo={bank.logo}
                onRefresh={refreshAll}
              />
            ))}
          </div>
        </div>
      )}

      {creditCards.length > 0 && (
        <div className="mb-6">
          <h2 className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-3">Tarjetas de Credito</h2>
          <div className="flex flex-wrap gap-4">
            {creditCards.map((card) => (
              <CreditCardVisual
                key={card.id}
                card={card}
                bankName={bank.name}
                bankLogo={bank.logo}
                onRefresh={refreshAll}
              />
            ))}
          </div>
        </div>
      )}

      {transactions.length > 0 && (
        <div>
          <h2 className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-3">Ultimos Movimientos</h2>
          <MovementsTable transactions={transactions} accounts={accounts} creditCards={creditCards} />
        </div>
      )}

      {showAccountModal && (
        <AddAccountModal
          bankId={bank.id}
          onClose={() => setShowAccountModal(false)}
          onCreated={() => { setShowAccountModal(false); refreshAll(); }}
        />
      )}

      {showCreditCardModal && (
        <AddCreditCardModal
          bankId={bank.id}
          onClose={() => setShowCreditCardModal(false)}
          onCreated={() => { setShowCreditCardModal(false); refreshAll(); }}
        />
      )}

      {showTransactionModal && (
        <TransactionModal
          paymentMethods={paymentMethods}
          onClose={() => setShowTransactionModal(false)}
          onSubmit={handleCreateTransaction}
        />
      )}
    </div>
  );
}
