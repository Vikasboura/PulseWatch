import React, { useState } from 'react';
import { Activity, Plus, ChevronDown, LogOut, CheckCircle, Radio } from 'lucide-react';
import { Project, User } from '../types';

interface NavbarProps {
  user: User | null;
  projects: Project[];
  activeProject: Project | null;
  onSelectProject: (proj: Project) => void;
  onOpenCreateProject: () => void;
  onLogout: () => void;
  wsConnected: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  projects,
  activeProject,
  onSelectProject,
  onOpenCreateProject,
  onLogout,
  wsConnected,
}) => {
  const [dropdownOpen, setDropdownOpen] = useState(false);

  return (
    <nav className="h-16 border-b border-dark-700 bg-dark-900/90 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-40">
      {/* Brand */}
      <div className="flex items-center space-x-6">
        <div className="flex items-center space-x-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-indigo-300 bg-clip-text text-transparent">
              PulseWatch
            </span>
            <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 ml-1.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              v1.0
            </span>
          </div>
        </div>

        {/* Project Switcher */}
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center space-x-2 px-3.5 py-1.5 rounded-lg bg-dark-800 hover:bg-dark-700 border border-dark-600 transition text-sm font-medium text-slate-200"
          >
            <div className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="max-w-[140px] truncate">{activeProject ? activeProject.name : 'Select Project'}</span>
            <ChevronDown className="w-4 h-4 text-slate-400" />
          </button>

          {dropdownOpen && (
            <div className="absolute left-0 mt-2 w-64 rounded-xl glow-card shadow-2xl py-1 z-50 animate-in fade-in zoom-in-95 duration-100">
              <div className="px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Projects
              </div>
              <div className="max-h-56 overflow-y-auto">
                {projects.map((proj) => (
                  <button
                    key={proj.id}
                    onClick={() => {
                      onSelectProject(proj);
                      setDropdownOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2 text-sm flex items-center justify-between hover:bg-dark-700/60 transition ${
                      activeProject?.id === proj.id ? 'text-indigo-400 font-semibold bg-dark-700/40' : 'text-slate-300'
                    }`}
                  >
                    <span className="truncate">{proj.name}</span>
                    {activeProject?.id === proj.id && <CheckCircle className="w-4 h-4 text-indigo-400" />}
                  </button>
                ))}
              </div>
              <div className="border-t border-dark-700 mt-1 pt-1">
                <button
                  onClick={() => {
                    setDropdownOpen(false);
                    onOpenCreateProject();
                  }}
                  className="w-full text-left px-3 py-2 text-sm text-indigo-400 hover:bg-indigo-500/10 flex items-center space-x-2 transition font-medium"
                >
                  <Plus className="w-4 h-4" />
                  <span>Create New Project</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center space-x-4">
        {/* WebSocket Realtime Status Pill */}
        <div
          className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-mono border ${
            wsConnected
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
              : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
          }`}
        >
          <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
          <span>{wsConnected ? 'LIVE STREAM' : 'OFFLINE'}</span>
        </div>

        {/* User Info & Logout */}
        <div className="flex items-center space-x-3 border-l border-dark-700 pl-4">
          <div className="text-right hidden sm:block">
            <div className="text-xs font-medium text-slate-200">{user?.full_name || 'Developer'}</div>
            <div className="text-[11px] text-slate-400 truncate max-w-[140px]">{user?.email}</div>
          </div>
          <button
            onClick={onLogout}
            title="Log Out"
            className="p-2 rounded-lg bg-dark-800 hover:bg-rose-500/10 hover:text-rose-400 border border-dark-600 text-slate-400 transition"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </nav>
  );
};
