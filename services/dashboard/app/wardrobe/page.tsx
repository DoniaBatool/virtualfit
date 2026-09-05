"use client";

import { useState, useEffect } from "react";
import { Shirt, Trash2, ArrowLeft, X, Download, ChevronLeft, ChevronRight } from "lucide-react";

const GATEWAY = process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://localhost:3004";

interface WardrobeItem {
  id: string;
  name: string;
  saved_at: string;
  result_image: string;
  feature?: string;
}

// ─── Lightbox ─────────────────────────────────────────────────────────────────
function Lightbox({
  items, index, onClose, onPrev, onNext, onDelete,
}: {
  items: WardrobeItem[];
  index: number;
  onClose: () => void;
  onPrev: () => void;
  onNext: () => void;
  onDelete: (id: string) => void;
}) {
  const item = items[index];

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape")     onClose();
      if (e.key === "ArrowLeft")  onPrev();
      if (e.key === "ArrowRight") onNext();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose, onPrev, onNext]);

  if (!item) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm"
      onClick={onClose}
    >
      {/* Modal card — stop propagation so clicks inside don't close */}
      <div
        className="relative max-w-2xl w-full mx-4 rounded-2xl overflow-hidden bg-slate-900 border border-amber-500/20 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top bar */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
          <div>
            <p className="text-white font-medium text-sm">{item.name}</p>
            <p className="text-slate-500 text-xs">{new Date(item.saved_at).toLocaleString()}</p>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={item.result_image}
              download={`virtualfit-${item.id}.jpg`}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all"
              title="Download"
            >
              <Download className="w-4 h-4" />
            </a>
            <button
              onClick={() => { onDelete(item.id); onClose(); }}
              className="p-2 rounded-lg text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-all"
              title="Delete"
            >
              <Trash2 className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Image */}
        <div className="relative bg-slate-950 flex items-center justify-center" style={{ minHeight: 400 }}>
          <img
            src={item.result_image}
            alt={item.name}
            className="max-h-[70vh] w-full object-contain"
          />

          {/* Prev / Next arrows */}
          {index > 0 && (
            <button
              onClick={onPrev}
              className="absolute left-3 top-1/2 -translate-y-1/2 p-2 rounded-full bg-black/60 text-white hover:bg-black/80 transition-all"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
          )}
          {index < items.length - 1 && (
            <button
              onClick={onNext}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-full bg-black/60 text-white hover:bg-black/80 transition-all"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Counter */}
        <div className="px-4 py-2 text-center text-xs text-slate-600">
          {index + 1} / {items.length}
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ─────────────────────────────────────────────────────────────────
export default function WardrobePage() {
  const [items, setItems]         = useState<WardrobeItem[]>([]);
  const [loading, setLoading]     = useState(true);
  const [lightboxIdx, setLightboxIdx] = useState<number | null>(null);

  useEffect(() => {
    fetch(`${GATEWAY}/api/wardrobe`)
      .then((r) => r.json())
      .then((d) => {
        const apiItems = Array.isArray(d) ? d : [];
        const local = JSON.parse(localStorage.getItem("wardrobe") || "[]");
        const ids = new Set(apiItems.map((i: WardrobeItem) => i.id));
        setItems([...apiItems, ...local.filter((i: WardrobeItem) => !ids.has(i.id))]);
      })
      .catch(() => {
        const local = JSON.parse(localStorage.getItem("wardrobe") || "[]");
        setItems(local);
      })
      .finally(() => setLoading(false));
  }, []);

  const remove = (id: string) => {
    const local = JSON.parse(localStorage.getItem("wardrobe") || "[]");
    localStorage.setItem("wardrobe", JSON.stringify(local.filter((i: WardrobeItem) => i.id !== id)));
    fetch(`${GATEWAY}/api/wardrobe/${id}`, { method: "DELETE" }).catch(() => {});
    setItems((prev) => prev.filter((i) => i.id !== id));
  };

  const featureEmoji: Record<string, string> = {
    clothes: "👔", bag: "👜", makeup: "💄",
    "eye-color": "👁️", hat: "🎩", shoes: "👟",
  };

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      <nav className="border-b border-amber-500/20 px-6 py-4 flex items-center gap-4">
        <a href="/tryon" className="text-slate-400 hover:text-white transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </a>
        <div className="flex items-center gap-2">
          <Shirt className="w-5 h-5 text-amber-400" />
          <span className="font-bold text-white">My Wardrobe</span>
        </div>
        <span className="text-sm text-slate-500">{items.length} saved looks</span>
      </nav>

      <div className="max-w-6xl mx-auto p-6">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <span className="w-6 h-6 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 gap-4 text-slate-600">
            <Shirt className="w-12 h-12 opacity-30" />
            <p>No saved looks yet — try something on!</p>
            <a href="/tryon"
              className="px-4 py-2 rounded-lg bg-amber-600 text-white text-sm hover:bg-amber-500 transition-colors">
              Go to Try-On
            </a>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            {items.map((item, idx) => (
              <div
                key={item.id}
                className="glass overflow-hidden group cursor-pointer hover:border-amber-500/40 transition-all"
                onClick={() => setLightboxIdx(idx)}
              >
                <div className="aspect-square bg-slate-900 relative">
                  {item.result_image ? (
                    <img
                      src={item.result_image}
                      alt={item.name}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-slate-700">
                      <Shirt className="w-10 h-10" />
                    </div>
                  )}
                  {/* Hover overlay */}
                  <div className="absolute inset-0 bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <span className="text-white text-xs font-medium bg-black/50 px-3 py-1 rounded-full">
                      Click to view
                    </span>
                  </div>
                  {/* Delete button */}
                  <button
                    onClick={(e) => { e.stopPropagation(); remove(item.id); }}
                    className="absolute top-2 right-2 p-1.5 rounded-lg bg-black/60 text-red-400 opacity-0 group-hover:opacity-100 transition-opacity hover:text-red-300"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
                <div className="p-3">
                  <p className="text-sm text-white font-medium truncate">
                    {item.feature ? featureEmoji[item.feature] + " " : ""}
                    {item.name || "Untitled"}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    {new Date(item.saved_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Lightbox */}
      {lightboxIdx !== null && (
        <Lightbox
          items={items}
          index={lightboxIdx}
          onClose={() => setLightboxIdx(null)}
          onPrev={() => setLightboxIdx((i) => Math.max(0, (i ?? 0) - 1))}
          onNext={() => setLightboxIdx((i) => Math.min(items.length - 1, (i ?? 0) + 1))}
          onDelete={remove}
        />
      )}
    </div>
  );
}
