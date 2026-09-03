"use client";

import { useState, useRef, useCallback } from "react";
import { Upload, Sparkles, Ruler, Zap, Save, RotateCcw, ChevronDown } from "lucide-react";

// Bypass gateway auth — talk directly to ML pipeline for demo
const GATEWAY = process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://localhost:8001";

// ─── Types ────────────────────────────────────────────────────────────────────
interface TryOnResult {
  request_id: string;
  result_image_b64?: string;
  result_url?: string;
  result_image_url?: string;
  recommended_size: string;
  fit_score: number;
  mode: string;
  inference_time_s: number;
  measurements?: {
    shoulder_cm: number;
    chest_cm: number;
    waist_cm: number;
    hip_cm: number;
  };
}

interface QuantumMatch {
  garment_id: string;
  name: string;
  category: string;
  quantum_score: number;
}

// ─── Upload Zone ──────────────────────────────────────────────────────────────
function UploadZone({
  label, icon, file, preview, onFile,
}: {
  label: string; icon: React.ReactNode;
  file: File | null; preview: string | null;
  onFile: (f: File) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);

  const handle = (f: File) => {
    if (f.type.startsWith("image/")) onFile(f);
  };

  return (
    <div
      className={`upload-zone flex flex-col items-center justify-center gap-3 p-6 min-h-[260px] relative overflow-hidden${drag ? " drag-over" : ""}`}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files[0]; if (f) handle(f); }}
    >
      {preview ? (
        <img src={preview} alt={label} className="absolute inset-0 w-full h-full object-cover rounded-xl" />
      ) : (
        <>
          <div className="text-brand-500 opacity-70">{icon}</div>
          <p className="text-sm text-slate-400 text-center">{label}</p>
          <p className="text-xs text-slate-600">Click or drag & drop</p>
        </>
      )}
      {preview && (
        <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity rounded-xl">
          <p className="text-white text-sm font-medium">Click to replace</p>
        </div>
      )}
      <input ref={inputRef} type="file" accept="image/*" className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) handle(f); }} />
    </div>
  );
}

// ─── Size Badge ───────────────────────────────────────────────────────────────
function SizeBadge({ size, score }: { size: string; score: number }) {
  const color = score >= 80 ? "text-green-400 border-green-500/30 bg-green-500/10"
    : score >= 60 ? "text-yellow-400 border-yellow-500/30 bg-yellow-500/10"
    : "text-red-400 border-red-500/30 bg-red-500/10";

  return (
    <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border ${color}`}>
      <div>
        <div className="text-2xl font-bold">{size}</div>
        <div className="text-xs opacity-70">Recommended</div>
      </div>
      <div className="ml-auto text-right">
        <div className="text-lg font-semibold">{score}%</div>
        <div className="text-xs opacity-70">Fit score</div>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function TryOnPage() {
  const [personFile, setPersonFile] = useState<File | null>(null);
  const [garmentFile, setGarmentFile] = useState<File | null>(null);
  const [personPreview, setPersonPreview] = useState<string | null>(null);
  const [garmentPreview, setGarmentPreview] = useState<string | null>(null);

  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState("");
  const [result, setResult] = useState<TryOnResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [bodyType, setBodyType] = useState("athletic");
  const [category, setCategory] = useState("shirt");
  const [quantumMatches, setQuantumMatches] = useState<QuantumMatch[]>([]);
  const [quantumLoading, setQuantumLoading] = useState(false);
  const [showMeasurements, setShowMeasurements] = useState(false);

  const onPersonFile = useCallback((f: File) => {
    setPersonFile(f);
    setPersonPreview(URL.createObjectURL(f));
    setResult(null);
  }, []);

  const onGarmentFile = useCallback((f: File) => {
    setGarmentFile(f);
    setGarmentPreview(URL.createObjectURL(f));
    setResult(null);
  }, []);

  const reset = () => {
    setPersonFile(null); setGarmentFile(null);
    setPersonPreview(null); setGarmentPreview(null);
    setResult(null); setError(null);
  };

  // ── Try-On ──────────────────────────────────────────────────────────────────
  const runTryOn = async () => {
    if (!personFile || !garmentFile) return;
    setLoading(true); setError(null); setResult(null);

    try {
      setStep("Segmenting person with SAM2...");
      const form = new FormData();
      form.append("person_image", personFile);
      form.append("garment_image", garmentFile);

      setStep("Running IDM-VTON diffusion model...");
      const res = await fetch(`${GATEWAY}/api/tryon`, { method: "POST", body: form });
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(e.error ?? `HTTP ${res.status}`);
      }

      const data = await res.json();

      // Poll if async
      if (data.status === "uploaded" && data.request_id) {
        setStep("Processing via DAPR pipeline...");
        let attempts = 0;
        while (attempts < 30) {
          await new Promise((r) => setTimeout(r, 3000));
          const poll = await fetch(`${GATEWAY}/api/tryon/${data.request_id}`);
          const pollData = await poll.json();
          if (pollData.status === "complete") {
            setResult({ ...pollData, request_id: data.request_id });
            break;
          }
          attempts++;
          setStep(`Waiting for result... (${attempts * 3}s)`);
        }
      } else {
        setResult(data);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Try-on failed");
    } finally {
      setLoading(false); setStep("");
    }
  };

  // ── Quantum Search ───────────────────────────────────────────────────────────
  const runQuantum = async () => {
    setQuantumLoading(true);
    try {
      const res = await fetch(`http://localhost:8001/api/quantum-match?body_type=${bodyType}&category=${category}&top_k=5`);
      const data = await res.json();
      setQuantumMatches(data.matches ?? data.top_matches ?? []);
    } catch {
      setQuantumMatches([]);
    } finally {
      setQuantumLoading(false);
    }
  };

  const resultImageSrc = result?.result_image_b64
    ? `data:image/jpeg;base64,${result.result_image_b64}`
    : result?.result_image_url ?? null;

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      {/* Nav */}
      <nav className="border-b border-amber-500/20 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="40" height="40">
            <defs>
              <clipPath id="vfbox"><rect width="100" height="100" rx="22"/></clipPath>
              <clipPath id="vflh"><rect x="0" y="0" width="50" height="100"/></clipPath>
              <clipPath id="vfrh"><rect x="50" y="0" width="50" height="100"/></clipPath>
              <linearGradient id="vfmg" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#160A00"/>
                <stop offset="14%" stopColor="#7A5010"/>
                <stop offset="38%" stopColor="#FAD868"/>
                <stop offset="56%" stopColor="#C99018"/>
                <stop offset="78%" stopColor="#6A4008"/>
                <stop offset="100%" stopColor="#160A00"/>
              </linearGradient>
              <pattern id="vflp" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(30 50 50)">
                <rect width="14" height="14" fill="#07101E"/>
                <rect width="10" height="14" fill="url(#vfmg)"/>
              </pattern>
              <pattern id="vfrp" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(-30 50 50)">
                <rect width="14" height="14" fill="#07101E"/>
                <rect width="10" height="14" fill="url(#vfmg)"/>
              </pattern>
              <radialGradient id="vftg" cx="50%" cy="8%" r="55%">
                <stop offset="0%" stopColor="#FFF2B0" stopOpacity="0.22"/>
                <stop offset="100%" stopColor="#C9A84C" stopOpacity="0"/>
              </radialGradient>
              <linearGradient id="vfrim" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#F8D468"/>
                <stop offset="45%" stopColor="#C9A84C"/>
                <stop offset="100%" stopColor="#7A5810"/>
              </linearGradient>
            </defs>
            <rect width="100" height="100" rx="22" fill="#07101E"/>
            <g clipPath="url(#vfbox)">
              <g clipPath="url(#vflh)"><rect width="100" height="100" fill="url(#vflp)"/></g>
              <g clipPath="url(#vfrh)"><rect width="100" height="100" fill="url(#vfrp)"/></g>
              <rect width="100" height="100" fill="url(#vftg)"/>
              <line x1="50" y1="0" x2="50" y2="100" stroke="#07101E" strokeWidth="2" opacity="0.55"/>
            </g>
            <rect x="2" y="2" width="96" height="96" rx="20.5" fill="none" stroke="url(#vfrim)" strokeWidth="3.5" opacity="0.88"/>
          </svg>
          <span className="font-bold text-lg text-white">VirtualFit</span>
          <span className="text-xs text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
            IDM-VTON · SAM2 · Qiskit
          </span>
        </div>
        <a href="/wardrobe" className="text-sm text-slate-400 hover:text-white transition-colors">
          My Wardrobe →
        </a>
      </nav>

      <div className="max-w-6xl mx-auto p-6 space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold text-white">AI Virtual Try-On</h1>
          <p className="text-slate-400 text-sm">Upload your photo + any garment → see yourself wearing it in seconds</p>
        </div>

        {/* ── Main split layout ── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Inputs */}
          <div className="glass p-6 space-y-5">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Upload Images</h2>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <p className="text-xs text-slate-500">Your Photo</p>
                <UploadZone
                  label="Full-body photo facing camera"
                  icon={<Upload className="w-8 h-8" />}
                  file={personFile} preview={personPreview}
                  onFile={onPersonFile}
                />
              </div>
              <div className="space-y-2">
                <p className="text-xs text-slate-500">Garment</p>
                <UploadZone
                  label="Shirt, dress, jacket, etc."
                  icon={<Upload className="w-8 h-8" />}
                  file={garmentFile} preview={garmentPreview}
                  onFile={onGarmentFile}
                />
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={runTryOn}
                disabled={!personFile || !garmentFile || loading}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-amber-600 hover:bg-amber-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold transition-all"
              >
                {loading ? (
                  <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />{step || "Processing..."}</>
                ) : (
                  <><Sparkles className="w-4 h-4" />Try On</>
                )}
              </button>
              {(personFile || garmentFile) && (
                <button onClick={reset} className="p-3 rounded-xl border border-slate-700 text-slate-400 hover:text-white hover:border-slate-500 transition-all">
                  <RotateCcw className="w-4 h-4" />
                </button>
              )}
            </div>

            {error && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">{error}</div>
            )}
          </div>

          {/* Right: Result */}
          <div className="glass p-6 space-y-5">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Result</h2>

            {resultImageSrc ? (
              <div className="space-y-4">
                <div className="relative rounded-xl overflow-hidden bg-slate-900" style={{ minHeight: 260 }}>
                  <img src={resultImageSrc} alt="Try-on result" className="w-full object-contain" />
                  <div className="absolute top-2 right-2 px-2 py-1 rounded-lg bg-black/60 text-xs text-white">
                    {result?.mode === "fallback" ? "⚡ Fast Preview" : "🧠 IDM-VTON"}
                  </div>
                </div>

                {result && (
                  <SizeBadge size={result.recommended_size ?? "M"} score={result.fit_score ?? 75} />
                )}

                {result?.measurements && (
                  <div>
                    <button
                      onClick={() => setShowMeasurements(!showMeasurements)}
                      className="flex items-center gap-2 text-xs text-amber-400 hover:text-amber-300"
                    >
                      <Ruler className="w-3 h-3" />
                      Body measurements
                      <ChevronDown className={`w-3 h-3 transition-transform ${showMeasurements ? "rotate-180" : ""}`} />
                    </button>
                    {showMeasurements && (
                      <div className="mt-2 grid grid-cols-2 gap-2">
                        {Object.entries(result.measurements).map(([k, v]) => (
                          <div key={k} className="px-3 py-2 rounded-lg bg-slate-800/50 text-xs">
                            <span className="text-slate-500 capitalize">{k.replace("_cm", "")} </span>
                            <span className="text-white font-medium">
                              {typeof v === "number" ? v.toFixed(1) : String(v)} cm
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                <div className="flex gap-2">
                  <a
                    href={resultImageSrc}
                    download="virtualfit-result.jpg"
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-slate-700 text-slate-300 hover:text-white hover:border-slate-500 text-sm transition-all"
                  >
                    Download
                  </a>
                  <button className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-600/20 border border-amber-500/30 text-amber-400 hover:text-amber-300 text-sm transition-all">
                    <Save className="w-3 h-3" />Save to Wardrobe
                  </button>
                </div>

                {result?.inference_time_s && (
                  <p className="text-xs text-slate-600 text-center">
                    Inference: {result.inference_time_s.toFixed(2)}s
                  </p>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center min-h-[260px] text-slate-600 space-y-3">
                <Sparkles className="w-10 h-10 opacity-30" />
                <p className="text-sm">Upload photos and click Try On</p>
              </div>
            )}
          </div>
        </div>

        {/* ── Quantum Search ── */}
        <div className="glass p-6 space-y-5">
          <div className="flex items-center gap-3">
            <Zap className="w-4 h-4 text-yellow-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
              Quantum Garment Search
            </h2>
            <span className="text-xs text-yellow-400/70 bg-yellow-500/10 px-2 py-0.5 rounded-full border border-yellow-500/20">
              Grover&apos;s O(√N)
            </span>
          </div>

          <div className="flex flex-wrap gap-3 items-end">
            <div className="space-y-1">
              <label className="text-xs text-slate-500">Body type</label>
              <select
                value={bodyType} onChange={(e) => setBodyType(e.target.value)}
                className="px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:border-amber-500"
              >
                {["lean", "athletic", "curvy", "petite", "all"].map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-slate-500">Category</label>
              <select
                value={category} onChange={(e) => setCategory(e.target.value)}
                className="px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:border-amber-500"
              >
                {["shirt", "blazer", "dress", "jacket", "pants", "hoodie", "sweater", "skirt"].map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
            </div>
            <button
              onClick={runQuantum}
              disabled={quantumLoading}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-yellow-500/20 border border-yellow-500/30 text-yellow-400 hover:text-yellow-300 hover:bg-yellow-500/30 text-sm transition-all disabled:opacity-50"
            >
              {quantumLoading
                ? <><span className="w-3 h-3 border-2 border-yellow-400/30 border-t-yellow-400 rounded-full animate-spin" />Searching...</>
                : <><Zap className="w-3 h-3" />Run Quantum Search</>}
            </button>
          </div>

          {quantumMatches.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
              {quantumMatches.map((m, i) => (
                <div key={m.garment_id ?? i}
                  className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-amber-500/40 transition-all cursor-pointer space-y-2"
                  onClick={() => {/* future: load garment */ }}
                >
                  <div className="w-full aspect-square rounded-lg bg-slate-700/50 flex items-center justify-center text-2xl">
                    👗
                  </div>
                  <div className="text-xs text-white font-medium truncate">{m.name}</div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-500">{m.category}</span>
                    <span className="text-xs text-yellow-400 font-semibold">
                      {(m.quantum_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
