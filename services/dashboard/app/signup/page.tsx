"use client";

import { useState } from "react";
import { Eye, EyeOff, UserPlus, Info } from "lucide-react";

function VFLogo({ size = 40 }: { size?: number }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width={size} height={size}>
      <defs>
        <clipPath id="vfbox2"><rect width="100" height="100" rx="22"/></clipPath>
        <clipPath id="vflh2"><rect x="0" y="0" width="50" height="100"/></clipPath>
        <clipPath id="vfrh2"><rect x="50" y="0" width="50" height="100"/></clipPath>
        <linearGradient id="vfmg2" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%"   stopColor="#160A00"/>
          <stop offset="14%"  stopColor="#7A5010"/>
          <stop offset="38%"  stopColor="#FAD868"/>
          <stop offset="56%"  stopColor="#C99018"/>
          <stop offset="78%"  stopColor="#6A4008"/>
          <stop offset="100%" stopColor="#160A00"/>
        </linearGradient>
        <pattern id="vflp2" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(30 50 50)">
          <rect width="14" height="14" fill="#07101E"/>
          <rect width="10" height="14" fill="url(#vfmg2)"/>
        </pattern>
        <pattern id="vfrp2" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(-30 50 50)">
          <rect width="14" height="14" fill="#07101E"/>
          <rect width="10" height="14" fill="url(#vfmg2)"/>
        </pattern>
        <radialGradient id="vftg2" cx="50%" cy="8%" r="55%">
          <stop offset="0%"   stopColor="#FFF2B0" stopOpacity="0.22"/>
          <stop offset="100%" stopColor="#C9A84C" stopOpacity="0"/>
        </radialGradient>
        <radialGradient id="vfts2" cx="50%" cy="90%" r="38%">
          <stop offset="0%"   stopColor="#000" stopOpacity="0.40"/>
          <stop offset="100%" stopColor="#000" stopOpacity="0"/>
        </radialGradient>
        <linearGradient id="vfrim2" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%"   stopColor="#F8D468"/>
          <stop offset="45%"  stopColor="#C9A84C"/>
          <stop offset="100%" stopColor="#7A5810"/>
        </linearGradient>
      </defs>
      <rect width="100" height="100" rx="22" fill="#07101E"/>
      <g clipPath="url(#vfbox2)">
        <g clipPath="url(#vflh2)"><rect width="100" height="100" fill="url(#vflp2)"/></g>
        <g clipPath="url(#vfrh2)"><rect width="100" height="100" fill="url(#vfrp2)"/></g>
        <rect width="100" height="100" fill="url(#vftg2)"/>
        <rect width="100" height="100" fill="url(#vfts2)"/>
        <line x1="50" y1="0" x2="50" y2="100" stroke="#07101E" strokeWidth="2" opacity="0.55"/>
      </g>
      <rect x="2" y="2" width="96" height="96" rx="20.5" fill="none" stroke="url(#vfrim2)" strokeWidth="3.5" opacity="0.88"/>
    </svg>
  );
}

const ML = process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://localhost:8001";

export default function SignupPage() {
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [showPwd, setShowPwd]   = useState(false);
  const [apiKey, setApiKey]     = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  // Admin email doesn't need YouCam keys
  const ADMIN = "donia1510aptech@gmail.com";
  const isAdmin = email.toLowerCase().trim() === ADMIN.toLowerCase();

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!isAdmin && (!apiKey || !secretKey)) {
      setError("Please enter your YouCam API key and secret");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }

    setLoading(true);
    try {
      const res  = await fetch(`${ML}/api/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          password,
          youcam_api_key:    isAdmin ? "" : apiKey,
          youcam_secret_key: isAdmin ? "" : secretKey,
        }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.detail || "Signup failed"); return; }
      localStorage.setItem("vf_token", data.token);
      localStorage.setItem("vf_user",  JSON.stringify(data.user));
      window.location.href = "/tryon";
    } catch {
      setError("Could not reach server — try again");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center py-8" style={{ background: "var(--bg)" }}>
      <div className="glass w-full max-w-md mx-4 p-8 rounded-2xl">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-8">
          <VFLogo size={44} />
          <span className="text-white font-bold text-xl">VirtualFit</span>
        </div>

        <h1 className="text-2xl font-bold text-white mb-1">Create account</h1>
        <p className="text-slate-400 text-sm mb-8">Start your virtual fitting room</p>

        <form onSubmit={submit} className="flex flex-col gap-4">
          {/* Email */}
          <div>
            <label className="block text-xs text-slate-400 mb-1.5">Email</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              placeholder="you@example.com"
              className="w-full px-4 py-2.5 rounded-lg bg-slate-800 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 text-sm"
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-xs text-slate-400 mb-1.5">Password</label>
            <div className="relative">
              <input
                type={showPwd ? "text" : "password"}
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                placeholder="Min. 6 characters"
                className="w-full px-4 py-2.5 pr-10 rounded-lg bg-slate-800 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 text-sm"
              />
              <button type="button" onClick={() => setShowPwd(p => !p)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300">
                {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* YouCam Keys — hidden for admin */}
          {!isAdmin && (
            <div className="border border-slate-700/50 rounded-xl p-4 bg-slate-800/30">
              <div className="flex items-center gap-2 mb-3">
                <Info className="w-4 h-4 text-amber-400 shrink-0" />
                <p className="text-xs text-slate-400">
                  Enter your{" "}
                  <a href="https://yce.makeupar.com/ai-api" target="_blank" rel="noopener"
                    className="text-amber-400 hover:underline">YouCam API</a>
                  {" "}keys (free tier available)
                </p>
              </div>

              <div className="flex flex-col gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">YouCam API Key</label>
                  <input
                    type="text"
                    value={apiKey}
                    onChange={e => setApiKey(e.target.value)}
                    placeholder="sk-..."
                    className="w-full px-4 py-2.5 rounded-lg bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">YouCam Secret Key</label>
                  <input
                    type="password"
                    value={secretKey}
                    onChange={e => setSecretKey(e.target.value)}
                    placeholder="MIGf..."
                    className="w-full px-4 py-2.5 rounded-lg bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 text-xs font-mono"
                  />
                </div>
              </div>
            </div>
          )}

          {isAdmin && email && (
            <p className="text-xs text-amber-400/80 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
              Admin account — YouCam keys are pre-configured
            </p>
          )}

          {error && (
            <p className="text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-medium text-sm transition-colors disabled:opacity-50"
          >
            {loading ? (
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <><UserPlus className="w-4 h-4" /> Create Account</>
            )}
          </button>
        </form>

        <p className="text-center text-xs text-slate-500 mt-6">
          Already have an account?{" "}
          <a href="/login" className="text-amber-400 hover:text-amber-300">Sign in</a>
        </p>
      </div>
    </div>
  );
}
