"use client";

import { useState } from "react";
import { Eye, EyeOff, UserPlus, Info } from "lucide-react";

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
        <div className="flex items-center gap-2 mb-8">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center">
            <span className="text-black font-black text-sm">VF</span>
          </div>
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
