import React, { useState, useEffect, useRef } from 'react';
import {
  LayoutDashboard,
  Terminal,
  BarChart3,
  BellRing,
  KeyRound,
  Layers,
} from 'lucide-react';
import { api, getAuthToken, clearAuthToken } from './api';
import { User, Project, LogItem } from './types';
import { Navbar } from './components/Navbar';
import { CreateProjectModal } from './components/CreateProjectModal';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { LogsPage } from './pages/LogsPage';
import { MetricsPage } from './pages/MetricsPage';
import { AlertsPage } from './pages/AlertsPage';
import { ApiKeysPage } from './pages/ApiKeysPage';

export function App() {
  const [user, setUser] = useState<User | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'logs' | 'metrics' | 'alerts' | 'api-keys'>('overview');
  
  // Realtime Live Stream State
  const [liveLogs, setLiveLogs] = useState<LogItem[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // Modals
  const [isCreateProjOpen, setIsCreateProjOpen] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);

  // Check auth session on mount
  useEffect(() => {
    checkSession();
    window.addEventListener('auth-expired', handleLogout);
    return () => window.removeEventListener('auth-expired', handleLogout);
  }, []);

  const checkSession = async () => {
    const token = getAuthToken();
    if (!token) {
      setInitialLoading(false);
      return;
    }

    try {
      const u = await api.getMe();
      setUser(u);
      await loadProjects();
    } catch {
      handleLogout();
    } finally {
      setInitialLoading(false);
    }
  };

  const loadProjects = async () => {
    try {
      const projs = await api.listProjects();
      setProjects(projs);
      if (projs.length > 0) {
        setActiveProject(projs[0]);
      }
    } catch (e) {
      console.error('Error fetching projects', e);
    }
  };

  const handleLogout = () => {
    clearAuthToken();
    setUser(null);
    setProjects([]);
    setActiveProject(null);
    if (wsRef.current) {
      wsRef.current.close();
    }
  };

  // Connect to WebSocket stream for active project
  useEffect(() => {
    if (!user || !activeProject) {
      if (wsRef.current) wsRef.current.close();
      setWsConnected(false);
      return;
    }

    const token = getAuthToken();
    if (!token) return;

    // Use current host or proxy
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/live/${activeProject.id}?token=${encodeURIComponent(token)}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'log') {
          setLiveLogs((prev) => {
            const next = [payload.data, ...prev];
            return next.slice(0, 500); // Buffer limit
          });
        }
      } catch (err) {
        console.error('Failed to parse websocket message', err);
      }
    };

    ws.onclose = () => {
      setWsConnected(false);
    };

    ws.onerror = (err) => {
      console.warn('WebSocket stream error', err);
      setWsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [user?.id, activeProject?.id]);

  if (initialLoading) {
    return (
      <div className="min-h-screen bg-dark-900 flex items-center justify-center text-slate-400 font-mono text-xs">
        <div className="flex items-center space-x-2">
          <div className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-ping" />
          <span>Initializing PulseWatch...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <LoginPage
        onLoginSuccess={async (u) => {
          setUser(u);
          await loadProjects();
        }}
      />
    );
  }

  return (
    <div className="min-h-screen bg-dark-900 text-slate-100 flex flex-col">
      {/* Top Navbar */}
      <Navbar
        user={user}
        projects={projects}
        activeProject={activeProject}
        onSelectProject={(p) => {
          setActiveProject(p);
          setLiveLogs([]);
        }}
        onOpenCreateProject={() => setIsCreateProjOpen(true)}
        onLogout={handleLogout}
        wsConnected={wsConnected}
      />

      {/* Main Layout */}
      <div className="flex-1 flex max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 gap-6">
        {/* Navigation Sidebar */}
        <aside className="w-56 shrink-0 hidden md:block space-y-1">
          {[
            { id: 'overview', label: 'Overview', icon: LayoutDashboard },
            { id: 'logs', label: 'Live Logs', icon: Terminal, badge: liveLogs.length > 0 ? liveLogs.length : undefined },
            { id: 'metrics', label: 'Metrics', icon: BarChart3 },
            { id: 'alerts', label: 'Alerts', icon: BellRing },
            { id: 'api-keys', label: 'API Keys', icon: KeyRound },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/25'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-dark-800'
                }`}
              >
                <div className="flex items-center space-x-2.5">
                  <Icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                </div>
                {tab.badge && (
                  <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-indigo-500/20 text-indigo-300 font-mono">
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </aside>

        {/* Content Area */}
        <main className="flex-1 min-w-0">
          {!activeProject ? (
            <div className="glow-card rounded-3xl p-12 text-center max-w-md mx-auto mt-12 space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center mx-auto">
                <Layers className="w-6 h-6" />
              </div>
              <h2 className="text-lg font-bold text-white">No Projects Available</h2>
              <p className="text-xs text-slate-400">
                Create your first monitoring project to generate an API key and start ingesting telemetry.
              </p>
              <button
                onClick={() => setIsCreateProjOpen(true)}
                className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition shadow-lg shadow-indigo-600/30"
              >
                Create Project
              </button>
            </div>
          ) : (
            <>
              {activeTab === 'overview' && (
                <DashboardPage project={activeProject} onNavigateTab={(t) => setActiveTab(t as any)} />
              )}
              {activeTab === 'logs' && (
                <LogsPage
                  project={activeProject}
                  liveLogs={liveLogs}
                  wsConnected={wsConnected}
                  onClearLiveLogs={() => setLiveLogs([])}
                />
              )}
              {activeTab === 'metrics' && <MetricsPage project={activeProject} />}
              {activeTab === 'alerts' && <AlertsPage project={activeProject} />}
              {activeTab === 'api-keys' && <ApiKeysPage project={activeProject} />}
            </>
          )}
        </main>
      </div>

      {/* Project Creation Modal */}
      <CreateProjectModal
        isOpen={isCreateProjOpen}
        onClose={() => setIsCreateProjOpen(false)}
        onCreated={(newProj) => {
          setProjects([newProj, ...projects]);
          setActiveProject(newProj);
        }}
      />
    </div>
  );
}

export default App;
