"use client";

import { useState, useEffect } from "react";
import { Shirt, Trash2, ArrowLeft } from "lucide-react";

const GATEWAY = process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://localhost:3004";

interface WardrobeItem {
  id: string;
  name: string;
  saved_at: string;
  result_image: string;
}

export default function WardrobePage() {
  const [items, setItems] = useState<WardrobeItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${GATEWAY}/api/wardrobe`)
      .then((r) => r.json())
      .then((d) => setItems(Array.isArray(d) ? d : []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);

  const remove = async (id: string) => {
    await fetch(`${GATEWAY}/api/wardrobe/${id}`, { method: "DELETE" });
    setItems((prev) => prev.filter((i) => i.id !== id));
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
          <div className="flex items-center justify-center h-64 text-slate-600">
            <span className="w-6 h-6 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
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
            {items.map((item) => (
              <div key={item.id} className="glass overflow-hidden group">
                <div className="aspect-square bg-slate-900 relative">
                  {item.result_image ? (
                    <img src={item.result_image} alt={item.name}
                      className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-slate-700">
                      <Shirt className="w-10 h-10" />
                    </div>
                  )}
                  <button
                    onClick={() => remove(item.id)}
                    className="absolute top-2 right-2 p-1.5 rounded-lg bg-black/60 text-red-400 opacity-0 group-hover:opacity-100 transition-opacity hover:text-red-300"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
                <div className="p-3">
                  <p className="text-sm text-white font-medium truncate">{item.name || "Untitled"}</p>
                  <p className="text-xs text-slate-500 mt-1">
                    {new Date(item.saved_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
