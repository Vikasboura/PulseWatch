import React, { useEffect, useState } from 'react';
import {
  FileText,
  AlertTriangle,
  Key,
  Activity,
  ArrowUpRight,
  Clock,
  ShieldAlert,
  Sparkles,
  Layers,
  RefreshCw,
  Box,
  BarChart3,
  Cpu,
  Zap,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Project, LogItem, AlertEvent, ApiKey } from '../types';
import { api } from '../api';
import { ServiceTopology3D } from '../components/ServiceTopology3D';
import { AIIncidentAnalyst } from '../components/AIIncidentAnalyst';

interface DashboardPageProps {
  project: Project;
  onNavigateTab: (tab: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ project, onNavigateTab }) => {
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [events, setEvents] = useState<AlertEvent[]>([]);
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState<'charts' | 'topology'>('charts');
  const [showAiAnalyst, setShowAiAnalyst] = useState(true);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000); // Polling every 10s
    return () => clearInterval(interval);
  }, [project.id]);

  const loadData = async () => {
    try {
      const [logsResp, eventsResp, keysResp] = await Promise.all([
        api.getLogs(project.id, { limit: 100 }),
        api.listEvents(project.id),
        api.listApiKeys(project.id),
      ]);
      setLogs(logsResp.items);
      setEvents(eventsResp);
      setApiKeys(keysResp);
    } catch (e) {
      console.error('Failed to load dashboard metrics', e);
    } finally {
      setLoading(false);
    }
  };

  const totalLogs = logs.length;
  const errorLogs = logs.filter((l) => l.level === 'ERROR' || l.level === 'CRITICAL').length;
  const errorRate = totalLogs > 0 ? ((errorLogs / totalLogs) * 100).toFixed(1) : '0.0';
  const activeIncidents = events.filter((e) => e.status === 'triggered');

  // Chart data: group logs by minute (last 15 minutes)
  const chartMap: Record<string, { time: string; total: number; errors: number }> = {};
  logs.forEach((log) => {
    const d = new Date(log.timestamp);
    const timeKey = `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
    if (!chartMap[timeKey]) {
      chartMap[timeKey] = { time: timeKey, total: 0, errors: 0 };
    }
    chartMap[timeKey].total += 1;
    if (log.level === 'ERROR' || log.level === 'CRITICAL') {
      chartMap[timeKey].errors += 1;
    }
  });

  const chartData = Object.values(chartMap).slice(-15).reverse();

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Bar with Live Indicator and View Mode Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900/60 border border-slate-800/80 p-3.5 rounded-xl backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1 bg-emerald-500/10 border border-emerald-500/30 rounded-full text-xs font-mono font-medium text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>LIVE INGESTION</span>
          </div>
          <span className="text-xs text-slate-400 font-mono hidden md:inline">
            Project: <strong className="text-slate-200">{project.name}</strong>
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
            <button
              onClick={() => setActiveView('charts')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition font-medium ${
                activeView === 'charts'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span>Metrics Timeline</span>
            </button>
            <button
              onClick={() => setActiveView('topology')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition font-medium ${
                activeView === 'topology'
                  ? 'bg-cyan-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Box className="w-3.5 h-3.5" />
              <span>3D Mesh Topology</span>
            </button>
          </div>

          <button
            onClick={() => setShowAiAnalyst(!showAiAnalyst)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition ${
              showAiAnalyst
                ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-300'
                : 'bg-slate-800/80 border-slate-700 text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span>AI Copilot</span>
          </button>

          <button
            onClick={loadData}
            className="p-1.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
            title="Refresh Metrics"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Active Incidents Banner */}
      {activeIncidents.length > 0 && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-rose-500/20 text-rose-400">
              <ShieldAlert className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="font-bold text-rose-300 text-xs sm:text-sm">
                {activeIncidents.length} Active Alert Incident{activeIncidents.length > 1 ? 's' : ''} Firing
              </div>
              <div className="text-xs text-rose-400/90 font-mono mt-0.5">{activeIncidents[0].message}</div>
            </div>
          </div>
          <button
            onClick={() => onNavigateTab('alerts')}
            className="px-3.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition shrink-0 active:scale-95"
          >
            Review Incident
          </button>
        </div>
      )}

      {/* Primary Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Ingestion */}
        <div className="bg-slate-900/80 border border-slate-800/90 rounded-xl p-5 shadow-lg relative overflow-hidden group hover:border-slate-700/80 transition-all">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider font-mono">Logged Events</span>
            <FileText className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-3xl font-extrabold text-white tracking-tight">{totalLogs}</div>
          <div className="mt-2 text-xs text-slate-400 flex items-center space-x-1 font-mono">
            <Clock className="w-3.5 h-3.5 text-slate-500" />
            <span>Recent telemetry window</span>
          </div>
        </div>

        {/* Error Rate */}
        <div className="bg-slate-900/80 border border-slate-800/90 rounded-xl p-5 shadow-lg relative overflow-hidden group hover:border-slate-700/80 transition-all">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider font-mono">Error Rate</span>
            <AlertTriangle className={`w-4 h-4 ${Number(errorRate) > 5 ? 'text-rose-400' : 'text-emerald-400'}`} />
          </div>
          <div className="text-3xl font-extrabold text-white tracking-tight">{errorRate}%</div>
          <div className="mt-2 text-xs text-slate-400 flex items-center space-x-1 font-mono">
            <span className="font-semibold text-rose-400">{errorLogs}</span>
            <span>error / critical events</span>
          </div>
        </div>

        {/* Active Alerts */}
        <div className="bg-slate-900/80 border border-slate-800/90 rounded-xl p-5 shadow-lg relative overflow-hidden group hover:border-slate-700/80 transition-all">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider font-mono">Triggered Incidents</span>
            <Activity className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-3xl font-extrabold text-white tracking-tight">{activeIncidents.length}</div>
          <div className="mt-2 text-xs text-slate-400 font-mono">
            {events.length} historical incidents recorded
          </div>
        </div>

        {/* API Keys */}
        <div className="bg-slate-900/80 border border-slate-800/90 rounded-xl p-5 shadow-lg relative overflow-hidden group hover:border-slate-700/80 transition-all">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider font-mono">Ingest API Keys</span>
            <Key className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-3xl font-extrabold text-white tracking-tight">{apiKeys.length}</div>
          <div className="mt-2 text-xs text-slate-400 font-mono">
            Retention: <span className="font-semibold text-slate-300">{project.retention_days} days</span>
          </div>
        </div>
      </div>

      {/* 3D Service Topology View (when toggled) */}
      {activeView === 'topology' && (
        <div className="space-y-2">
          <ServiceTopology3D
            totalErrors={errorLogs}
            onNodeClick={(id) => {
              if (id === 'database' || id === 'payments') {
                setShowAiAnalyst(true);
              }
            }}
          />
        </div>
      )}

      {/* AI Telemetry Copilot & Root Cause Analysis Section */}
      {showAiAnalyst && (
        <AIIncidentAnalyst projectId={project.id} />
      )}

      {/* Main Charts & Recent Logs Section */}
      {activeView === 'charts' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Ingestion & Error Timeline */}
          <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800/90 rounded-xl p-6 shadow-xl backdrop-blur-md">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider font-mono">
                  Event Traffic & Error Volume
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">Time-series distribution across telemetry stream</p>
              </div>
              <button
                onClick={() => onNavigateTab('logs')}
                className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center space-x-1"
              >
                <span>Live Explorer</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="h-64 w-full">
              {chartData.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs font-mono">
                  <span>No logs ingested yet in current window.</span>
                  <span className="mt-1 text-slate-600">Run demo_app/app.py to generate live events</span>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                      </linearGradient>
                      <linearGradient id="colorErrors" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.6} />
                        <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="time" stroke="#475569" fontSize={11} tickLine={false} />
                    <YAxis stroke="#475569" fontSize={11} tickLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#090d16',
                        borderColor: '#1e293b',
                        borderRadius: '8px',
                        fontSize: '12px',
                        fontFamily: 'monospace',
                      }}
                      itemStyle={{ color: '#e2e8f0' }}
                    />
                    <Area
                      type="monotone"
                      dataKey="total"
                      name="Total Events"
                      stroke="#06b6d4"
                      fillOpacity={1}
                      fill="url(#colorTotal)"
                    />
                    <Area
                      type="monotone"
                      dataKey="errors"
                      name="Errors"
                      stroke="#f43f5e"
                      fillOpacity={1}
                      fill="url(#colorErrors)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Quick Recent Log Stream Snapshot */}
          <div className="bg-slate-900/80 border border-slate-800/90 rounded-xl p-6 shadow-xl backdrop-blur-md flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider font-mono">
                  Recent Telemetry Log
                </h2>
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              </div>

              <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
                {logs.slice(0, 5).map((log) => (
                  <div
                    key={log.id}
                    className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800/80 text-xs font-mono"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                          log.level === 'ERROR' || log.level === 'CRITICAL'
                            ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                            : log.level === 'WARNING'
                            ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                            : 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
                        }`}
                      >
                        {log.level}
                      </span>
                      <span className="text-[10px] text-slate-500">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="text-slate-300 truncate">{log.message}</div>
                  </div>
                ))}

                {logs.length === 0 && (
                  <div className="text-center py-10 text-xs text-slate-500 font-mono">
                    No log entries recorded yet.
                  </div>
                )}
              </div>
            </div>

            <button
              onClick={() => onNavigateTab('logs')}
              className="w-full mt-4 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-semibold transition text-center active:scale-[0.98]"
            >
              Open Full Live Terminal
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
