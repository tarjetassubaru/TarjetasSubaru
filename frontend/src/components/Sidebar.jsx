import { useState } from "react";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { getBanks, reorderBanks, deleteBank } from "../api/banks";
import AddBankModal from "./AddBankModal";

function SortableBank({ bank, onSelect, onDelete }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: bank.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={() => onSelect(bank)}
      className="flex items-center gap-3 px-5 py-3 cursor-pointer transition-colors group hover:bg-[#1a1d2e]"
    >
      <div className="text-gray-600 cursor-grab active:cursor-grabbing shrink-0">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <circle cx="5" cy="4" r="1.5" />
          <circle cx="11" cy="4" r="1.5" />
          <circle cx="5" cy="8" r="1.5" />
          <circle cx="11" cy="8" r="1.5" />
          <circle cx="5" cy="12" r="1.5" />
          <circle cx="11" cy="12" r="1.5" />
        </svg>
      </div>
      <div className="w-8 h-8 rounded-full bg-gray-800 flex items-center justify-center overflow-hidden shrink-0">
        {bank.logo ? (
            <img
              src={bank.logo}
            alt={bank.name}
            className="w-6 h-6 object-contain"
          />
        ) : (
          <span className="text-xs font-bold text-gray-500">
            {bank.name.charAt(0)}
          </span>
        )}
      </div>
      <span className="text-sm text-gray-300 font-medium flex-1 truncate">
        {bank.name}
      </span>
      <button
        onClick={(e) => onDelete(e, bank.id)}
        className="text-gray-600 hover:text-red-400 transition-colors text-sm p-1 opacity-0 group-hover:opacity-100"
        title="Eliminar banco"
      >
        x
      </button>
    </div>
  );
}

export default function Sidebar({ banks, setBanks, onSelectBank }) {
  const [showModal, setShowModal] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  function handleDragEnd(event) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = banks.findIndex((b) => b.id === active.id);
    const newIndex = banks.findIndex((b) => b.id === over.id);

    const items = arrayMove(banks, oldIndex, newIndex);
    setBanks(items);

    reorderBanks(items.map((b) => b.id)).catch(async () => {
      const res = await getBanks();
      setBanks(res);
    });
  }

  async function handleDelete(e, id) {
    e.stopPropagation();
    try {
      await deleteBank(id);
      setBanks((prev) => prev.filter((b) => b.id !== id));
    } catch (err) {
      alert(err.message);
    }
  }

  return (
    <aside className="w-72 min-h-screen bg-[#0f1117] border-r border-gray-800 flex flex-col">
      <div className="px-5 py-6 border-b border-gray-800">
        <h2 className="text-sm font-semibold tracking-widest text-gray-400 uppercase">
          Bancos
        </h2>
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={banks.map((b) => b.id)}
          strategy={verticalListSortingStrategy}
        >
          <div className="flex-1 overflow-y-auto py-2">
            {banks.map((bank) => (
              <SortableBank
                key={bank.id}
                bank={bank}
                onSelect={onSelectBank}
                onDelete={handleDelete}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      <div className="p-4 border-t border-gray-800">
        <button
          onClick={() => setShowModal(true)}
          className="w-full py-2.5 px-4 bg-[#1a1d2e] hover:bg-[#252840] text-gray-300 text-sm font-medium rounded-lg border border-gray-700/50 transition-colors cursor-pointer"
        >
          + Agregar banco
        </button>
      </div>

      {showModal && (
        <AddBankModal
          onClose={() => setShowModal(false)}
          onCreated={(bank) => {
            setBanks((prev) => [...prev, bank]);
            setShowModal(false);
          }}
        />
      )}
    </aside>
  );
}
