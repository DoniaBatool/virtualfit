"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Upload, Sparkles, RotateCcw, Save, Check } from "lucide-react";

// ─── Full geometric logo (same as landing page) ───────────────────────────────
function VFLogo({ size = 40 }: { size?: number }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width={size} height={size}>
      <defs>
        <clipPath id="vfbox"><rect width="100" height="100" rx="22"/></clipPath>
        <clipPath id="vflh"><rect x="0" y="0" width="50" height="100"/></clipPath>
        <clipPath id="vfrh"><rect x="50" y="0" width="50" height="100"/></clipPath>
        <linearGradient id="vfmg" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%"   stopColor="#160A00"/>
          <stop offset="14%"  stopColor="#7A5010"/>
          <stop offset="38%"  stopColor="#FAD868"/>
          <stop offset="56%"  stopColor="#C99018"/>
          <stop offset="78%"  stopColor="#6A4008"/>
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
          <stop offset="0%"   stopColor="#FFF2B0" stopOpacity="0.22"/>
          <stop offset="100%" stopColor="#C9A84C" stopOpacity="0"/>
        </radialGradient>
        <radialGradient id="vfts" cx="50%" cy="90%" r="38%">
          <stop offset="0%"   stopColor="#000" stopOpacity="0.40"/>
          <stop offset="100%" stopColor="#000" stopOpacity="0"/>
        </radialGradient>
        <linearGradient id="vfrim" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%"   stopColor="#F8D468"/>
          <stop offset="45%"  stopColor="#C9A84C"/>
          <stop offset="100%" stopColor="#7A5810"/>
        </linearGradient>
      </defs>
      <rect width="100" height="100" rx="22" fill="#07101E"/>
      <g clipPath="url(#vfbox)">
        <g clipPath="url(#vflh)"><rect width="100" height="100" fill="url(#vflp)"/></g>
        <g clipPath="url(#vfrh)"><rect width="100" height="100" fill="url(#vfrp)"/></g>
        <rect width="100" height="100" fill="url(#vftg)"/>
        <rect width="100" height="100" fill="url(#vfts)"/>
        <line x1="50" y1="0" x2="50" y2="100" stroke="#07101E" strokeWidth="2" opacity="0.55"/>
      </g>
      <rect x="2" y="2" width="96" height="96" rx="20.5" fill="none" stroke="url(#vfrim)" strokeWidth="3.5" opacity="0.88"/>
    </svg>
  );
}

// ─── Toast notification ────────────────────────────────────────────────────────
function Toast({ message, onDone }: { message: string; onDone: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDone, 2500);
    return () => clearTimeout(t);
  }, [onDone]);
  return (
    <div className="fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-xl bg-slate-800 border border-amber-500/40 shadow-2xl text-white text-sm animate-fade-in">
      <div className="w-6 h-6 rounded-full bg-amber-500/20 border border-amber-500/50 flex items-center justify-center">
        <Check className="w-3.5 h-3.5 text-amber-400" />
      </div>
      {message}
    </div>
  );
}

const ML = process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://localhost:8001";

// ─── Feature config ────────────────────────────────────────────────────────────
type Feature = "clothes" | "bag" | "makeup" | "eye-color" | "hat" | "shoes";

const FEATURES: { id: Feature; emoji: string; label: string }[] = [
  { id: "clothes",   emoji: "👔", label: "Clothes"   },
  { id: "bag",       emoji: "👜", label: "Bag"        },
  { id: "makeup",    emoji: "💄", label: "Makeup"     },
  { id: "eye-color", emoji: "👁️",  label: "Eye Color"  },
  { id: "hat",       emoji: "🎩", label: "Hat"        },
  { id: "shoes",     emoji: "👟", label: "Shoes"      },
];

const MAKEUP_PRESETS = [
  { id: "natural",   label: "Natural",    desc: "Subtle blush + nude gloss" },
  { id: "glam",      label: "Glam",       desc: "Smoky eye + bold red lips"  },
  { id: "bold_lips", label: "Bold Lips",  desc: "Deep berry matte lips"      },
  { id: "smoky_eye", label: "Smoky Eye",  desc: "Black smoky eye + dark lip" },
];

const EYE_COLORS = [
  { id: "blue",     label: "Blue",     hex: "#2E86AB" },
  { id: "green",    label: "Green",    hex: "#2D6A4F" },
  { id: "gray",     label: "Gray",     hex: "#6B7280" },
  { id: "hazel",    label: "Hazel",    hex: "#8B6914" },
  { id: "violet",   label: "Violet",   hex: "#7B2D8B" },
  { id: "amber",    label: "Amber",    hex: "#C97D12" },
  { id: "ice_blue", label: "Ice Blue", hex: "#A8D8EA" },
  { id: "honey",    label: "Honey",    hex: "#B5860D" },
];

const BAG_STYLES = [
  { id: "random",                    label: "Auto"             },
  { id: "style_parisian_chic",       label: "Parisian Chic"    },
  { id: "style_urban_chic",          label: "Urban Chic"       },
  { id: "style_mediterranean_chic",  label: "Mediterranean"    },
  { id: "style_art_deco_style",      label: "Art Deco"         },
];

const CLOTHES_CATEGORIES = [
  { id: "upper_body", label: "Top (shirt, jacket, …)" },
  { id: "lower_body", label: "Bottom (pants, skirt, …)" },
  { id: "full_body",  label: "Full outfit (dress, …)"  },
];


// ─── Upload Zone ──────────────────────────────────────────────────────────────
function UploadZone({
  label, file, preview, onFile,
}: {
  label: string;
  file: File | null; preview: string | null;
  onFile: (f: File) => void;
}) {
  const ref  = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);

  const handle = (f: File) => { if (f.type.startsWith("image/")) onFile(f); };

  return (
    <div
      className={`upload-zone flex flex-col items-center justify-center gap-3 p-6 min-h-[240px] relative overflow-hidden cursor-pointer${drag ? " drag-over" : ""}`}
      onClick={() => ref.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files[0]; if (f) handle(f); }}
    >
      {preview ? (
        <img src={preview} alt={label} className="absolute inset-0 w-full h-full object-cover rounded-xl" />
      ) : (
        <>
          <Upload className="w-8 h-8 text-amber-500 opacity-60" />
          <p className="text-sm text-slate-400 text-center">{label}</p>
          <p className="text-xs text-slate-600">Click or drag & drop</p>
        </>
      )}
      {preview && (
        <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity rounded-xl">
          <p className="text-white text-sm font-medium">Click to replace</p>
        </div>
      )}
      <input ref={ref} type="file" accept="image/*" className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) handle(f); }} />
    </div>
  );
}


// ─── Result Panel ─────────────────────────────────────────────────────────────
function ResultPanel({
  resultSrc, mode, inferenceTime, onSave,
}: {
  resultSrc: string | null;
  mode?: string; inferenceTime?: number;
  onSave: () => void;
}) {
  const label = mode?.startsWith("youcam") ? "✨ YouCam AI" : "⚡ Preview";

  if (!resultSrc) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[240px] text-slate-600 space-y-3">
        <Sparkles className="w-10 h-10 opacity-30" />
        <p className="text-sm">Result will appear here</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="relative rounded-xl overflow-hidden bg-slate-900">
        <img src={resultSrc} alt="Try-on result" className="w-full object-contain" />
        <div className="absolute top-2 right-2 px-2 py-1 rounded-lg bg-black/60 text-xs text-white">
          {label}
        </div>
      </div>

      <div className="flex gap-2">
        <a
          href={resultSrc}
          download="virtualfit-result.jpg"
          className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-slate-700 text-slate-300 hover:text-white hover:border-slate-500 text-sm transition-all"
        >
          Download
        </a>
        <button
          onClick={onSave}
          className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-600/20 border border-amber-500/30 text-amber-400 hover:text-amber-300 text-sm transition-all"
        >
          <Save className="w-3 h-3" />Save
        </button>
      </div>

      {inferenceTime && (
        <p className="text-xs text-slate-600 text-center">
          {inferenceTime.toFixed(2)}s · YouCam cloud
        </p>
      )}
    </div>
  );
}


// ─── Main Page ────────────────────────────────────────────────────────────────
export default function TryOnPage() {
  const [feature, setFeature] = useState<Feature>("clothes");

  // Shared images
  const [personFile, setPersonFile]     = useState<File | null>(null);
  const [personPreview, setPersonPreview] = useState<string | null>(null);
  const [itemFile, setItemFile]         = useState<File | null>(null);
  const [itemPreview, setItemPreview]   = useState<string | null>(null);

  // Feature settings
  const [clothesCategory, setClothesCategory] = useState("upper_body");
  const [bagGender, setBagGender]             = useState("female");
  const [bagStyle, setBagStyle]               = useState("random");
  const [makeupPreset, setMakeupPreset]       = useState("natural");
  const [eyeColor, setEyeColor]               = useState("blue");
  const [customEyeHex, setCustomEyeHex]       = useState("#2E86AB");
  const [useCustomEye, setUseCustomEye]       = useState(false);

  // UI state
  const [loading, setLoading]   = useState(false);
  const [step, setStep]         = useState("");
  const [error, setError]       = useState<string | null>(null);
  const [resultB64, setResultB64] = useState<string | null>(null);
  const [resultMeta, setResultMeta] = useState<{ mode: string; inference_time_s: number } | null>(null);
  const [toast, setToast]       = useState<string | null>(null);

  // Derived
  const resultSrc = resultB64 ? `data:image/jpeg;base64,${resultB64}` : null;

  const needsItem = !["makeup", "eye-color"].includes(feature);

  const onPerson = useCallback((f: File) => {
    setPersonFile(f);
    setPersonPreview(URL.createObjectURL(f));
    setResultB64(null);
  }, []);

  const onItem = useCallback((f: File) => {
    setItemFile(f);
    setItemPreview(URL.createObjectURL(f));
    setResultB64(null);
  }, []);

  const switchFeature = (f: Feature) => {
    setFeature(f);
    setItemFile(null);
    setItemPreview(null);
    setResultB64(null);
    setError(null);
    setStep("");
  };

  const reset = () => {
    setPersonFile(null); setPersonPreview(null);
    setItemFile(null); setItemPreview(null);
    setResultB64(null); setError(null);
  };

  const saveToWardrobe = () => {
    if (!resultSrc) return;
    const item = {
      id: Date.now().toString(),
      feature,
      name: `${feature} · ${new Date().toLocaleDateString()}`,
      saved_at: new Date().toISOString(),
      result_image: resultSrc,
    };
    const existing = (() => { try { return JSON.parse(localStorage.getItem("wardrobe") || "[]"); } catch { return []; } })();
    localStorage.setItem("wardrobe", JSON.stringify([item, ...existing]));
    setToast("Saved to wardrobe!");
  };

  // ── Submit ─────────────────────────────────────────────────────────────────
  const submit = async () => {
    if (!personFile) return;
    if (needsItem && !itemFile) return;

    setLoading(true); setError(null); setResultB64(null);

    try {
      const form = new FormData();
      form.append("person_image", personFile);

      let url = "";
      switch (feature) {
        case "clothes":
          form.append("garment_image", itemFile!);
          url = `${ML}/api/tryon?category=${clothesCategory}`;
          setStep("Fitting garment with YouCam AI…");
          break;

        case "bag":
          form.append("bag_image", itemFile!);
          url = `${ML}/api/bag?gender=${bagGender}&style=${bagStyle}`;
          setStep("Placing bag with YouCam AI…");
          break;

        case "makeup":
          url = `${ML}/api/makeup?preset=${makeupPreset}`;
          setStep("Applying makeup with YouCam AI…");
          break;

        case "eye-color": {
          const c = useCustomEye ? customEyeHex : eyeColor;
          url = `${ML}/api/eye-color?color=${encodeURIComponent(c)}`;
          setStep("Changing eye color with YouCam AI…");
          break;
        }

        case "hat":
          form.append("hat_image", itemFile!);
          url = `${ML}/api/hat`;
          setStep("Fitting hat with YouCam AI…");
          break;

        case "shoes":
          form.append("shoes_image", itemFile!);
          url = `${ML}/api/shoes`;
          setStep("Fitting shoes with YouCam AI…");
          break;
      }

      const res = await fetch(url, { method: "POST", body: form });
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(e.detail ?? e.error ?? `HTTP ${res.status}`);
      }

      const data = await res.json();
      setResultB64(data.result_image_b64);
      setResultMeta({ mode: data.mode, inference_time_s: data.inference_time_s });

    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false); setStep("");
    }
  };

  // ── Item upload label ──────────────────────────────────────────────────────
  const itemLabel: Record<Feature, string> = {
    clothes:    "Garment (shirt, dress, jacket…)",
    bag:        "Handbag or purse photo",
    makeup:     "",
    "eye-color": "",
    hat:        "Hat or cap photo",
    shoes:      "Shoe / footwear photo",
  };

  const canSubmit = personFile && (!needsItem || itemFile) && !loading;

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      {/* Nav */}
      <nav className="border-b border-amber-500/20 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <VFLogo size={40} />
          <span className="font-bold text-lg text-white">VirtualFit</span>
          <span className="text-xs text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
            YouCam AI
          </span>
        </div>
        <a href="/wardrobe" className="text-sm text-slate-400 hover:text-white transition-colors">
          My Wardrobe →
        </a>
      </nav>

      <div className="max-w-5xl mx-auto p-6 space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold text-white">AI Virtual Try-On</h1>
          <p className="text-slate-400 text-sm">
            Powered by YouCam (Perfect Corp) — photorealistic cloud inference
          </p>
        </div>

        {/* ── Feature Tabs ── */}
        <div className="flex flex-wrap gap-2 justify-center">
          {FEATURES.map((f) => (
            <button
              key={f.id}
              onClick={() => switchFeature(f.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all border ${
                feature === f.id
                  ? "bg-amber-600 border-amber-500 text-white"
                  : "bg-slate-800/50 border-slate-700 text-slate-400 hover:text-white hover:border-slate-500"
              }`}
            >
              <span>{f.emoji}</span>
              <span>{f.label}</span>
            </button>
          ))}
        </div>

        {/* ── Main Split ── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Inputs */}
          <div className="glass p-6 space-y-5">
            {/* Person upload — always shown */}
            <div className="space-y-2">
              <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">
                {feature === "makeup" || feature === "eye-color"
                  ? "Your Face / Portrait"
                  : "Your Photo (full-body)"}
              </p>
              <UploadZone
                label={
                  feature === "makeup" || feature === "eye-color"
                    ? "Close-up portrait / selfie"
                    : "Full-body photo facing camera"
                }
                file={personFile} preview={personPreview}
                onFile={onPerson}
              />
            </div>

            {/* Item upload — clothes/bag/hat/shoes */}
            {needsItem && (
              <div className="space-y-2">
                <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">
                  {FEATURES.find((f) => f.id === feature)?.emoji} {FEATURES.find((f) => f.id === feature)?.label} Photo
                </p>
                <UploadZone
                  label={itemLabel[feature]}
                  file={itemFile} preview={itemPreview}
                  onFile={onItem}
                />
              </div>
            )}

            {/* Feature-specific settings */}

            {/* Clothes: category */}
            {feature === "clothes" && (
              <div className="space-y-2">
                <p className="text-xs text-slate-500">Garment Category</p>
                <div className="flex flex-col gap-2">
                  {CLOTHES_CATEGORIES.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => setClothesCategory(c.id)}
                      className={`px-3 py-2 rounded-lg text-sm text-left transition-all border ${
                        clothesCategory === c.id
                          ? "bg-amber-600/20 border-amber-500/50 text-amber-300"
                          : "bg-slate-800/50 border-slate-700 text-slate-400 hover:text-white"
                      }`}
                    >
                      {c.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Bag: gender + style */}
            {feature === "bag" && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <p className="text-xs text-slate-500">Gender</p>
                  <div className="flex gap-2">
                    {["female", "male"].map((g) => (
                      <button key={g}
                        onClick={() => setBagGender(g)}
                        className={`flex-1 py-2 rounded-lg text-sm capitalize transition-all border ${
                          bagGender === g
                            ? "bg-amber-600/20 border-amber-500/50 text-amber-300"
                            : "bg-slate-800/50 border-slate-700 text-slate-400 hover:text-white"
                        }`}
                      >{g}</button>
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  <p className="text-xs text-slate-500">Style Preset</p>
                  <div className="flex flex-col gap-1">
                    {BAG_STYLES.map((s) => (
                      <button key={s.id}
                        onClick={() => setBagStyle(s.id)}
                        className={`px-3 py-2 rounded-lg text-sm text-left transition-all border ${
                          bagStyle === s.id
                            ? "bg-amber-600/20 border-amber-500/50 text-amber-300"
                            : "bg-slate-800/50 border-slate-700 text-slate-400 hover:text-white"
                        }`}
                      >{s.label}</button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Makeup: presets */}
            {feature === "makeup" && (
              <div className="space-y-2">
                <p className="text-xs text-slate-500">Makeup Look</p>
                <div className="grid grid-cols-2 gap-2">
                  {MAKEUP_PRESETS.map((p) => (
                    <button key={p.id}
                      onClick={() => setMakeupPreset(p.id)}
                      className={`px-3 py-3 rounded-xl text-sm text-left transition-all border space-y-1 ${
                        makeupPreset === p.id
                          ? "bg-pink-600/20 border-pink-500/50 text-pink-300"
                          : "bg-slate-800/50 border-slate-700 text-slate-400 hover:text-white"
                      }`}
                    >
                      <div className="font-medium">{p.label}</div>
                      <div className="text-xs opacity-70">{p.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Eye Color: swatches */}
            {feature === "eye-color" && (
              <div className="space-y-3">
                <p className="text-xs text-slate-500">Eye Color</p>
                <div className="flex flex-wrap gap-2">
                  {EYE_COLORS.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => { setEyeColor(c.id); setUseCustomEye(false); }}
                      title={c.label}
                      className={`w-9 h-9 rounded-full border-2 transition-all ${
                        !useCustomEye && eyeColor === c.id
                          ? "border-white scale-110"
                          : "border-transparent hover:border-slate-400"
                      }`}
                      style={{ background: c.hex }}
                    />
                  ))}
                </div>
                <div className="flex items-center gap-3">
                  <label className="text-xs text-slate-500">Custom:</label>
                  <input
                    type="color"
                    value={customEyeHex}
                    onChange={(e) => { setCustomEyeHex(e.target.value); setUseCustomEye(true); }}
                    onClick={() => setUseCustomEye(true)}
                    className="w-10 h-8 rounded cursor-pointer border border-slate-700 bg-slate-800"
                  />
                  {useCustomEye && (
                    <span className="text-xs text-amber-400">{customEyeHex}</span>
                  )}
                </div>
                <p className="text-xs text-slate-500">
                  Selected: <span className="text-white">
                    {useCustomEye ? customEyeHex : EYE_COLORS.find((c) => c.id === eyeColor)?.label}
                  </span>
                </p>
              </div>
            )}

            {/* Submit */}
            <div className="flex gap-3 pt-1">
              <button
                onClick={submit}
                disabled={!canSubmit}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-amber-600 hover:bg-amber-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold transition-all"
              >
                {loading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    {step || "Processing…"}
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    {FEATURES.find((f) => f.id === feature)?.emoji} Try On
                  </>
                )}
              </button>
              {(personFile || itemFile) && (
                <button
                  onClick={reset}
                  className="p-3 rounded-xl border border-slate-700 text-slate-400 hover:text-white hover:border-slate-500 transition-all"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              )}
            </div>

            {error && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                {error.includes("YOUCAM_API_KEY") || error.includes("YouCam API key")
                  ? "⚠️ YouCam API key not set. Register free at yce.makeupar.com and add YOUCAM_API_KEY to .env"
                  : error}
              </div>
            )}
          </div>

          {/* Right: Result */}
          <div className="glass p-6 space-y-5">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Result</h2>
            <ResultPanel
              resultSrc={resultSrc}
              mode={resultMeta?.mode}
              inferenceTime={resultMeta?.inference_time_s}
              onSave={saveToWardrobe}
            />
          </div>
        </div>

        {/* ── Tips ── */}
        <div className="glass p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">📸 Photo Tips for Best Results</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs text-slate-500">
            {[
              { feature: "👔 Clothes",   tip: "Full-body shot, neutral pose, plain background" },
              { feature: "👜 Bag",       tip: "Full-body or waist-up, arms relaxed at sides"  },
              { feature: "💄 Makeup",    tip: "Close-up portrait, good lighting, face forward" },
              { feature: "👁️ Eye Color",  tip: "Close-up selfie, eyes open, good lighting"      },
              { feature: "🎩 Hat",       tip: "Head and shoulders visible, straight-on shot"   },
              { feature: "👟 Shoes",     tip: "Full-body photo with feet clearly visible"       },
            ].map((t) => (
              <div key={t.feature} className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/50">
                <div className="text-slate-300 font-medium mb-1">{t.feature}</div>
                {t.tip}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>

    {toast && <Toast message={toast} onDone={() => setToast(null)} />}
  );
}
