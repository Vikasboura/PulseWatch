import React, { useState } from 'react';
import { X, FolderPlus } from 'lucide-react';
import { api } from '../api';
import { Project } from '../types';

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (proj: Project) => void;
}

export const CreateProjectModal: React.FC<CreateProjectModalProps> = ({
  isOpen,
  onClose,
  onCreated,
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [retentionDays, setRetentionDays] = useState(30);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError('');

    try {
      const proj = await api.createProject({
        name: name.trim(),
        description: description.trim() || undefined,
        retention_days: retentionDays,
      });
      onCreated(proj);
      onClose();
      setName('');
      setDescription('');
    } catch (err: any) {
      setError(err.message || 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="glow-card w-full max-w-md rounded-2xl p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between pb-4 border-b border-dark-700">
          <div className="flex items-center space-x-2 text-slate-100 font-bold text-lg">
            <FolderPlus className="w-5 h-5 text-indigo-400" />
            <span>Create New Project</span>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-dark-700 text-slate-400 hover:text-white transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase text-slate-400 mb-1.5">
              Project Name *
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Production API, Auth Service"
              className="w-full px-3.5 py-2.5 rounded-xl bg-dark-800 border border-dark-600 focus:border-indigo-500 focus:outline-none text-slate-100 placeholder-slate-500 text-sm transition"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-slate-400 mb-1.5">
              Description (Optional)
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of the monitored system"
              className="w-full px-3.5 py-2.5 rounded-xl bg-dark-800 border border-dark-600 focus:border-indigo-500 focus:outline-none text-slate-100 placeholder-slate-500 text-sm transition"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-slate-400 mb-1.5">
              Data Retention (Days)
            </label>
            <select
              value={retentionDays}
              onChange={(e) => setRetentionDays(Number(e.target.value))}
              className="w-full px-3.5 py-2.5 rounded-xl bg-dark-800 border border-dark-600 focus:border-indigo-500 focus:outline-none text-slate-100 text-sm transition"
            >
              <option value={7}>7 Days (Free tier)</option>
              <option value={14}>14 Days</option>
              <option value={30}>30 Days (Standard)</option>
              <option value={90}>90 Days (Extended)</option>
            </select>
          </div>

          <div className="pt-2 flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-dark-700 hover:bg-dark-600 text-slate-300 text-sm font-medium transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-semibold transition shadow-lg shadow-indigo-600/30"
            >
              {loading ? 'Creating...' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
