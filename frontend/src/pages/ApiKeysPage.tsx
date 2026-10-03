import React, { useState, useEffect } from 'react';
import {
  Key,
  Plus,
  Trash2,
  Copy,
  Check,
  AlertTriangle,
  Code,
  Shield,
  Terminal,
} from 'lucide-react';
import { Project, ApiKey, ApiKeyCreated } from '../types';
import { api } from '../api';

interface ApiKeysPageProps {
  project: Project;
}

export const ApiKeysPage: React.FC<ApiKeysPageProps> = ({ project }) => {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [keyName, setKeyName] = useState('');
  const [createdKey, setCreatedKey] = useState<ApiKeyCreated | null>(null);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadKeys();
  }, [project.id]);

  const loadKeys = async () => {
    try {
      const data = await api.listApiKeys(project.id);
      setKeys(data);
    } catch (err) {
      console.error('Failed to load API keys', err);
    }
  };

  const handleGenerateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyName.trim()) return;
    setLoading(true);
    try {
      const res = await api.createApiKey(project.id, keyName.trim());
      setCreatedKey(res);
      setKeyName('');
      await loadKeys();
    } catch (err: any) {
      alert(err.message || 'Failed to create key');
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async (keyId: string) => {
    if (!confirm('Are you sure you want to revoke this API key? Apps using it will immediately stop being able to ingest data.')) {
      return;
    }
    try {
      await api.revokeApiKey(project.id, keyId);
      setKeys(keys.filter((k) => k.id !== keyId));
    } catch (err: any) {
      alert(err.message || 'Failed to revoke key');
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="glow-card rounded-2xl p-5 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400">
            <Key className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white">Ingestion API Keys</h2>
            <p className="text-xs text-slate-400">Authenticate external applications, daemons, and SDK clients</p>
          </div>
        </div>

        <button
          onClick={() => {
            setCreatedKey(null);
            setIsModalOpen(true);
          }}
          className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 transition"
        >
          <Plus className="w-4 h-4" />
          <span>Generate New Key</span>
        </button>
      </div>

      {/* Keys Table */}
      <div className="glow-card rounded-2xl border border-dark-700 shadow-xl overflow-hidden">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-dark-800 text-slate-400 border-b border-dark-700 text-[11px] uppercase tracking-wider">
            <tr>
              <th className="px-5 py-3 font-semibold">Key Name</th>
              <th className="px-5 py-3 font-semibold">Key Prefix</th>
              <th className="px-5 py-3 font-semibold">Status</th>
              <th className="px-5 py-3 font-semibold">Last Used</th>
              <th className="px-5 py-3 font-semibold">Created At</th>
              <th className="px-5 py-3 font-semibold text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-700/60">
            {keys.map((k) => (
              <tr key={k.id} className="hover:bg-dark-800/50 transition">
                <td className="px-5 py-3.5 font-bold text-white">{k.name}</td>
                <td className="px-5 py-3.5">
                  <span className="px-2 py-0.5 rounded bg-dark-700 text-indigo-300 border border-dark-600">
                    {k.key_prefix}...
                  </span>
                </td>
                <td className="px-5 py-3.5">
                  <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    <span>Active</span>
                  </span>
                </td>
                <td className="px-5 py-3.5 text-slate-400">
                  {k.last_used_at ? new Date(k.last_used_at).toLocaleString() : 'Never'}
                </td>
                <td className="px-5 py-3.5 text-slate-400">{new Date(k.created_at).toLocaleDateString()}</td>
                <td className="px-5 py-3.5 text-right">
                  <button
                    onClick={() => handleRevoke(k.id)}
                    title="Revoke key"
                    className="p-1.5 rounded-lg hover:bg-rose-500/10 text-slate-500 hover:text-rose-400 transition"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
            {keys.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center py-12 text-slate-500">
                  No API keys generated yet. Click "Generate New Key" to create one.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Integration Code Sample Card */}
      <div className="glow-card rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex items-center space-x-2 text-white font-bold text-sm">
          <Terminal className="w-4 h-4 text-indigo-400" />
          <span>Quick Integration Example</span>
        </div>
        <p className="text-xs text-slate-400">
          Install the PulseWatch Python client in your app to begin streaming metrics & error logs automatically:
        </p>

        <div className="p-4 rounded-xl bg-dark-900 border border-dark-700 font-mono text-xs text-slate-300 space-y-2 overflow-x-auto">
          <div className="text-slate-500"># 1. Install PulseWatch SDK</div>
          <div className="text-indigo-400">pip install pulsewatch</div>
          <div className="text-slate-500 pt-2"># 2. Attach logging handler and send metrics</div>
          <div><span className="text-violet-400">from</span> pulsewatch <span className="text-violet-400">import</span> PulseWatchClient, PulseWatchHandler</div>
          <div><span className="text-violet-400">import</span> logging</div>
          <div className="pt-1">client = PulseWatchClient(api_key=<span className="text-emerald-300">"pw_live_YOUR_KEY"</span>)</div>
          <div>logging.getLogger().addHandler(PulseWatchHandler(client))</div>
          <div className="pt-1">client.send_metric(name=<span className="text-emerald-300">"payment_latency_ms"</span>, value=<span className="text-amber-300">142.5</span>)</div>
        </div>
      </div>

      {/* Generate Key Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glow-card w-full max-w-lg rounded-2xl p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            {!createdKey ? (
              <>
                <div className="flex items-center space-x-2 text-white font-bold text-lg pb-4 border-b border-dark-700">
                  <Key className="w-5 h-5 text-indigo-400" />
                  <span>Generate Ingestion API Key</span>
                </div>

                <form onSubmit={handleGenerateKey} className="mt-4 space-y-4 text-xs">
                  <div>
                    <label className="block uppercase font-semibold text-slate-400 mb-1.5">
                      Key Name / Identifier *
                    </label>
                    <input
                      type="text"
                      required
                      value={keyName}
                      onChange={(e) => setKeyName(e.target.value)}
                      placeholder="e.g. Production Cluster, Celery Worker, Staging App"
                      className="w-full px-3.5 py-2.5 rounded-xl bg-dark-800 border border-dark-600 focus:border-indigo-500 focus:outline-none text-slate-100 text-sm"
                    />
                  </div>

                  <div className="pt-2 flex justify-end space-x-3">
                    <button
                      type="button"
                      onClick={() => setIsModalOpen(false)}
                      className="px-4 py-2 rounded-xl bg-dark-700 text-slate-300 font-medium"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={loading || !keyName.trim()}
                      className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition shadow-lg shadow-indigo-600/30"
                    >
                      {loading ? 'Generating...' : 'Generate Key'}
                    </button>
                  </div>
                </form>
              </>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center space-x-2 text-emerald-400 font-bold text-lg pb-2 border-b border-dark-700">
                  <Shield className="w-5 h-5" />
                  <span>API Key Generated Successfully</span>
                </div>

                <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-start space-x-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
                  <span>
                    Copy and store this secret key in a safe place. For security reasons, it will <strong>never be displayed again</strong>.
                  </span>
                </div>

                <div>
                  <label className="block text-[11px] uppercase font-semibold text-slate-400 mb-1">
                    Secret API Key
                  </label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="text"
                      readOnly
                      value={createdKey.raw_key}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-dark-900 border border-dark-600 font-mono text-xs text-indigo-300 select-all"
                    />
                    <button
                      onClick={() => handleCopy(createdKey.raw_key)}
                      className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center space-x-1.5 transition shrink-0"
                    >
                      {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                      <span>{copied ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    onClick={() => {
                      setCreatedKey(null);
                      setIsModalOpen(false);
                    }}
                    className="px-5 py-2 rounded-xl bg-dark-700 hover:bg-dark-600 text-white text-xs font-semibold"
                  >
                    Done
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
