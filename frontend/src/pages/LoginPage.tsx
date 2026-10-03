import React, { useState } from 'react';
import { Activity, ShieldCheck, Zap, ArrowRight } from 'lucide-react';
import { api, setAuthToken } from '../api';
import { User } from '../types';

interface LoginPageProps {
  onLoginSuccess: (user: User) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (isRegister) {
        await api.register({ email, password, full_name: fullName || undefined });
      }
      const tokenResp = await api.login({ email, password });
      setAuthToken(tokenResp.access_token);
      const user = await api.getMe();
      onLoginSuccess(user);
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-dark-900 flex flex-col justify-center items-center px-4 relative overflow-hidden">
      {/* Background ambient lighting */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-indigo-600/15 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-violet-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-500 shadow-xl shadow-indigo-500/25 mb-4">
            <Activity className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">PulseWatch</h1>
          <p className="mt-2 text-sm text-slate-400">
            Lightweight, low-latency observability for small agile teams.
          </p>
        </div>

        {/* Card */}
        <div className="glow-card rounded-3xl p-8 shadow-2xl border border-white/10">
          <div className="flex border-b border-dark-700 pb-3 mb-6">
            <button
              onClick={() => { setIsRegister(false); setError(''); }}
              className={`flex-1 pb-2 text-sm font-semibold transition text-center ${
                !isRegister ? 'text-indigo-400 border-b-2 border-indigo-500' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => { setIsRegister(true); setError(''); }}
              className={`flex-1 pb-2 text-sm font-semibold transition text-center ${
                isRegister ? 'text-indigo-400 border-b-2 border-indigo-500' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Create Account
            </button>
          </div>

          {error && (
            <div className="mb-5 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-medium">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-400 mb-1.5">
                  Full Name
                </label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Alex Rivera"
                  className="w-full px-4 py-3 rounded-xl bg-dark-800 border border-dark-600 focus:border-indigo-500 focus:outline-none text-slate-100 placeholder-slate-500 text-sm transition"
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold uppercase text-slate-400 mb-1.5">
                Work Email *
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="dev@startup.io"
                className="w-full px-4 py-3 rounded-xl bg-dark-800 border border-dark-600 focus:border-indigo-500 focus:outline-none text-slate-100 placeholder-slate-500 text-sm transition"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-slate-400 mb-1.5">
                Password *
              </label>
              <input
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-4 py-3 rounded-xl bg-dark-800 border border-dark-600 focus:border-indigo-500 focus:outline-none text-slate-100 placeholder-slate-500 text-sm transition"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-3 px-4 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 disabled:opacity-50 text-white font-bold text-sm transition shadow-lg shadow-indigo-600/30 flex items-center justify-center space-x-2"
            >
              <span>{loading ? 'Authenticating...' : isRegister ? 'Create Account' : 'Sign In to Dashboard'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Highlights */}
          <div className="mt-8 pt-6 border-t border-dark-700/80 grid grid-cols-2 gap-4 text-[11px] text-slate-400">
            <div className="flex items-center space-x-2">
              <Zap className="w-4 h-4 text-indigo-400 shrink-0" />
              <span>Zero-lag live log stream</span>
            </div>
            <div className="flex items-center space-x-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Hashed API key security</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
