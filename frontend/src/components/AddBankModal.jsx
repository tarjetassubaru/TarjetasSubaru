import { useState, useRef } from "react";
import { createBank } from "../api/banks";

export default function AddBankModal({ onClose, onCreated }) {
  const [name, setName] = useState("");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef(null);

  function handleFileChange(e) {
    const f = e.target.files[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
  }

  function handleRemoveFile() {
    setFile(null);
    setPreview(null);
    if (fileRef.current) fileRef.current.value = "";
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError("");
    try {
      const fd = new FormData();
      fd.append("name", name.trim());
      if (file) fd.append("logo", file);
      const bank = await createBank(fd);
      onCreated(bank);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-[#0f1117] border border-gray-800 rounded-xl w-full max-w-sm mx-4 p-6 shadow-2xl">
        <h3 className="text-lg font-semibold text-gray-200 mb-4">
          Nuevo banco
        </h3>
        <form onSubmit={handleSubmit}>
          <label className="block mb-2 text-sm text-gray-400">Nombre</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ej: Banco de Chile"
            autoFocus
            className="w-full px-3 py-2.5 bg-[#1a1d2e] border border-gray-700 rounded-lg text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-gray-500 transition-colors"
          />

          <label className="block mb-2 mt-4 text-sm text-gray-400">Logo</label>

          {preview ? (
            <div className="relative w-20 h-20 mb-2">
              <img
                src={preview}
                alt="Preview"
                className="w-20 h-20 rounded-lg object-cover border border-gray-700"
              />
              <button
                type="button"
                onClick={handleRemoveFile}
                className="absolute -top-2 -right-2 w-5 h-5 bg-red-500/80 hover:bg-red-500 text-white rounded-full text-xs flex items-center justify-center cursor-pointer"
              >
                x
              </button>
            </div>
          ) : (
            <div
              onClick={() => fileRef.current?.click()}
              className="w-20 h-20 rounded-lg border-2 border-dashed border-gray-700 hover:border-gray-500 flex items-center justify-center cursor-pointer transition-colors mb-2"
            >
              <span className="text-gray-500 text-2xl leading-none">+</span>
            </div>
          )}

          <input
            ref={fileRef}
            type="file"
            accept=".png,.jpg,.jpeg,.webp,.svg"
            onChange={handleFileChange}
            className="hidden"
          />

          {error && (
            <p className="text-red-400 text-xs mt-2">{error}</p>
          )}

          <div className="flex justify-end gap-3 mt-5">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-400 hover:text-gray-300 transition-colors cursor-pointer"
            >
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
