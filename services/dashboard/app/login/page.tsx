"use client";

import { useState } from "react";
import { Eye, EyeOff, LogIn } from "lucide-react";

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

const ML = process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://localhost:8001";

export default function LoginPage() {
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [showPwd, setShowPwd]   = useState(false);
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res  = await fetch(`${ML}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.detail || "Login failed"); return; }
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
    <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg)" }}>
      <div className="glass w-full max-w-md mx-4 p-8 rounded-2xl">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-8">
          <VFLogo size={44} />
          <span className="text-white font-bold text-xl">VirtualFit</span>
        </div>

        <h1 className="text-2xl font-bold text-white mb-1">Welcome back</h1>
        <p className="text-slate-400 text-sm mb-8">Sign in to your account</p>

        <form onSubmit={submit} className="flex flex-col gap-4">
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

          <div>
            <label className="block text-xs text-slate-400 mb-1.5">Password</label>
            <div className="relative">
              <input
                type={showPwd ? "text" : "password"}
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                placeholder="••••••••"
                className="w-full px-4 py-2.5 pr-10 rounded-lg bg-slate-800 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 text-sm"
              />
              <button
                type="button"
                onClick={() => setShowPwd(p => !p)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
              >
                {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

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
              <><LogIn className="w-4 h-4" /> Sign In</>
            )}
          </button>
        </form>

        <p className="text-center text-xs text-slate-500 mt-6">
          Don&apos;t have an account?{" "}
          <a href="/signup" className="text-amber-400 hover:text-amber-300">Sign up</a>
        </p>
      </div>
    </div>
  );
}
