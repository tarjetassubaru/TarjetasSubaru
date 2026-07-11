import { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import BankView from "./components/BankView";
import { getBanks } from "./api/banks";

function App() {
  const [banks, setBanks] = useState([]);
  const [selectedBank, setSelectedBank] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadBanks = () => {
    getBanks()
      .then((data) => {
        setBanks(data);
        if (selectedBank) {
          const updated = data.find((b) => b.id === selectedBank.id);
          if (updated) setSelectedBank(updated);
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadBanks();
  }, []);

  return (
    <div className="flex min-h-screen bg-[#0a0b10] text-gray-300">
      <Sidebar
        banks={banks}
        setBanks={setBanks}
        onSelectBank={setSelectedBank}
      />
      <main className="flex-1 flex items-center justify-center">
        {loading ? (
          <p className="text-gray-600 text-sm">Cargando...</p>
        ) : selectedBank ? (
          <BankView bank={selectedBank} refreshBanks={loadBanks} />
        ) : (
          <div className="text-center">
            <p className="text-gray-600 text-sm">
              Selecciona un banco del sidebar
            </p>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
