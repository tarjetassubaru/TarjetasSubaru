const API_URL = "http://localhost:8000/api";

export async function getBanks() {
  const res = await fetch(`${API_URL}/banks`);
  if (!res.ok) throw new Error("Error al obtener bancos");
  return res.json();
}

export async function createBank(formData) {
  const res = await fetch(`${API_URL}/banks`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Error al crear banco");
  return res.json();
}

export async function updateBank(id, data) {
  const res = await fetch(`${API_URL}/banks/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Error al actualizar banco");
  return res.json();
}

export async function reorderBanks(ids) {
  const res = await fetch(`${API_URL}/banks/reorder`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  });
  if (!res.ok) throw new Error("Error al reordenar bancos");
  return res.json();
}

export async function deleteBank(id) {
  const res = await fetch(`${API_URL}/banks/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Error al eliminar banco");
}

export async function getBankData(bankId) {
  const res = await fetch(`${API_URL}/banks/${bankId}/data`);
  if (!res.ok) throw new Error("Error al obtener datos del banco");
  return res.json();
}

export async function getAccounts(bankId) {
  const res = await fetch(`${API_URL}/accounts?bank_id=${bankId}`);
  if (!res.ok) throw new Error("Error al obtener cuentas");
  return res.json();
}

export async function createAccount(data) {
  const res = await fetch(`${API_URL}/accounts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Error al crear cuenta");
  return res.json();
}

export async function updateAccount(id, data) {
  const res = await fetch(`${API_URL}/accounts/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Error al actualizar cuenta");
  return res.json();
}

export async function deleteAccount(id) {
  const res = await fetch(`${API_URL}/accounts/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Error al eliminar cuenta");
}

export async function applyInterest(accountId) {
  const res = await fetch(`${API_URL}/accounts/${accountId}/apply-interest`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Error al calcular intereses");
  return res.json();
}

export async function getCreditCards(bankId) {
  const res = await fetch(`${API_URL}/credit-cards?bank_id=${bankId}`);
  if (!res.ok) throw new Error("Error al obtener tarjetas de credito");
  return res.json();
}

export async function createCreditCard(data) {
  const res = await fetch(`${API_URL}/credit-cards`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Error al crear tarjeta de credito");
  return res.json();
}

export async function updateCreditCard(id, data) {
  const res = await fetch(`${API_URL}/credit-cards/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Error al actualizar tarjeta de credito");
  return res.json();
}

export async function deleteCreditCard(id) {
  const res = await fetch(`${API_URL}/credit-cards/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Error al eliminar tarjeta de credito");
}

export async function getTransactions(bankId) {
  const res = await fetch(`${API_URL}/transactions?bank_id=${bankId}`);
  if (!res.ok) throw new Error("Error al obtener movimientos");
  return res.json();
}

export async function createTransaction(data) {
  const res = await fetch(`${API_URL}/transactions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Error al registrar movimiento");
  return res.json();
}
