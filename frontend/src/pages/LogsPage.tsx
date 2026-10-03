import React, { useState, useEffect, useRef } from 'react';
import {
  Search,
  Pause,
  Play,
  Trash2,
  Filter,
  ArrowDown,
  Info,
  AlertTriangle,
  XCircle,
  Copy,
  Check,
  Code,
} from 'lucide-react';
import { Project, LogItem } from '../types';
import { api } from '../api';

interface LogsPageProps {
  project: Project;
  liveLogs: LogItem[];
  wsConnected: boolean;
  onClearLiveLogs: () => void;
}

export const LogsPage: React.FC<LogsPageProps> = ({
  project,
  liveLogs,
  wsConnected,
  onClearLiveLogs,
}) => {
  const [historicalLogs, setHistoricalLogs] = useState<LogItem[]>([]);
  const [selectedLevel, setSelectedLevel] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [isPaused, setIsPaused] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [selectedLog, setSelectedLog] = useState<LogItem | null>(null);
  const [copied, setCopied] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const logsEndRef = useRef<HTMLDivElement>(null);

  // Load initial historical logs on project change
  useEffect(() => {
    loadHistoricalLogs();
  }, [project.id, selectedLevel]);

  const loadHistoricalLogs = async () => {
    setLoadingHistory(true);
    try {
      const resp = await api.getLogs(project.id, {
        level: selectedLevel === 'ALL' ? undefined : selectedLevel,
        limit: 100,
      });
      setHistoricalLogs(resp.items);
    } catch (e) {
      console.error('Failed to load logs history', e);
    } finally {
      setLoadingHistory(false);
    }
  };

  // Combine live logs and historical logs, deduplicated by id or timestamp+msg
  const combinedLogs = React.useMemo(() => {
    const seenIds = new Set<number>();
    const all: LogItem[] = [];

    // Realtime incoming logs first if not paused
    liveLogs.forEach((l) => {
      if (l.project_id === project.id && !seenIds.has(l.id)) {
        seenIds.add(l.id);
        all.push(l);
      }
    });

    // Append historical records
    historicalLogs.forEach((l) => {
      if (!seenIds.has(l.id)) {
        seenIds.add(l.id);
        all.push(l);
      }
    });

    // Filter by search
    return all.filter((item) => {
      const matchesLevel =
        selectedLevel === 'ALL' || item.level.toUpperCase() === selectedLevel;
      const matchesSearch =
        !searchQuery ||
        item.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
        JSON.stringify(item.metadata || {}).toLowerCase().includes(searchQuery.toLowerCase());
      return matchesLevel && matchesSearch;
    });
  }, [liveLogs, historicalLogs, project.id, selectedLevel, searchQuery]);

  useEffect(() => {
    if (autoScroll && !isPaused && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [liveLogs.length, autoScroll, isPaused]);

  const handleCopyJson = (obj: any) => {
    navigator.clipboard.writeText(JSON.stringify(obj, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getLevelBadge = (level: string) => {
    switch (level) {
      case 'ERROR':
      case 'CRITICAL':
        return 'bg-rose-500/15 text-rose-400 border-rose-500/30';
      case 'WARNING':
        return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
      case 'DEBUG':
        return 'bg-slate-500/15 text-slate-400 border-slate-500/30';
      default:
        return 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30';
    }
  };

  return (
    <div className="space-y-4">
      {/* Control Bar */}
      <div className="glow-card rounded-2xl p-4 shadow-xl flex flex-wrap items-center justify-between gap-4">
        {/* Search */}
        <div className="relative flex-1 min-w-[240px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search logs by keyword or metadata..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-dark-800 border border-dark-600 focus:border-indigo-500 focus:outline-none text-slate-100 placeholder-slate-500 text-xs font-mono transition"
          />
        </div>

        {/* Level Filters */}
        <div className="flex items-center space-x-1 bg-dark-800 p-1 rounded-xl border border-dark-600 text-xs font-semibold">
          {['ALL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'].map((lvl) => (
            <button
              key={lvl}
              onClick={() => setSelectedLevel(lvl)}
              className={`px-3 py-1.5 rounded-lg transition ${
                selectedLevel === lvl
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {lvl}
            </button>
          ))}
        </div>

        {/* Actions */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold transition ${
              isPaused
                ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                : 'bg-dark-800 hover:bg-dark-700 text-slate-300 border-dark-600'
            }`}
          >
            {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
            <span>{isPaused ? 'Resume Stream' : 'Pause'}</span>
          </button>

          <button
            onClick={onClearLiveLogs}
            title="Clear stream buffer"
            className="p-2 rounded-xl bg-dark-800 hover:bg-rose-500/10 hover:text-rose-400 text-slate-400 border border-dark-600 transition"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Log Stream Terminal Window */}
      <div className="glow-card rounded-2xl border border-dark-700 shadow-2xl overflow-hidden flex flex-col h-[600px]">
        {/* Terminal Header */}
        <div className="px-4 py-2.5 bg-dark-800 border-b border-dark-700 flex items-center justify-between text-xs font-mono text-slate-400">
          <div className="flex items-center space-x-2">
            <div className="flex space-x-1.5">
              <div className="w-2.5 h-2.5 rounded-full bg-rose-500/70" />
              <div className="w-2.5 h-2.5 rounded-full bg-amber-500/70" />
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/70" />
            </div>
            <span className="font-semibold text-slate-300 ml-2">stream:/{project.name}</span>
          </div>

          <div className="flex items-center space-x-3 text-[11px]">
            <span>{combinedLogs.length} events buffered</span>
            <label className="flex items-center space-x-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded border-dark-600 text-indigo-600 focus:ring-0"
              />
              <span>Auto-scroll</span>
            </label>
          </div>
        </div>

        {/* Logs Table / Rows */}
        <div className="flex-1 overflow-y-auto font-mono text-xs p-2 space-y-1">
          {combinedLogs.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-2">
              <Code className="w-8 h-8 text-slate-600" />
              <span>Waiting for logs matching filter criteria...</span>
            </div>
          ) : (
            combinedLogs.map((log) => (
              <div
                key={log.id || `${log.timestamp}-${log.message}`}
                onClick={() => setSelectedLog(log)}
                className="group px-3 py-2 rounded-lg hover:bg-dark-800/90 cursor-pointer transition flex items-start space-x-3 border border-transparent hover:border-dark-700"
              >
                <span className="text-[11px] text-slate-500 shrink-0 select-none pt-0.5">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
                <span
                  className={`text-[10px] font-bold px-1.5 py-0.5 rounded border uppercase shrink-0 ${getLevelBadge(
                    log.level
                  )}`}
                >
                  {log.level}
                </span>
                <span className="text-slate-200 flex-1 truncate">{log.message}</span>
                {log.metadata && Object.keys(log.metadata).length > 0 && (
                  <span className="text-[10px] text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded shrink-0">
                    JSON
                  </span>
                )}
              </div>
            ))
          )}
          <div ref={logsEndRef} />
        </div>
      </div>

      {/* Log Detail Drawer Modal */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glow-card w-full max-w-2xl rounded-2xl p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-4 border-b border-dark-700">
              <div className="flex items-center space-x-2">
                <span className={`text-xs font-bold px-2 py-0.5 rounded border ${getLevelBadge(selectedLog.level)}`}>
                  {selectedLog.level}
                </span>
                <span className="text-sm font-mono text-slate-400">
                  {new Date(selectedLog.timestamp).toISOString()}
                </span>
              </div>
              <button
                onClick={() => setSelectedLog(null)}
                className="p-1 rounded-lg hover:bg-dark-700 text-slate-400 hover:text-white"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <div className="mt-4 space-y-4">
              <div>
                <label className="text-xs uppercase font-semibold text-slate-500">Message</label>
                <div className="mt-1 p-3 rounded-xl bg-dark-800 border border-dark-700 font-mono text-xs text-slate-100 select-all">
                  {selectedLog.message}
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs uppercase font-semibold text-slate-500">Metadata Payload</label>
                  <button
                    onClick={() => handleCopyJson(selectedLog.metadata)}
                    className="flex items-center space-x-1 text-xs text-indigo-400 hover:text-indigo-300"
                  >
                    {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? 'Copied' : 'Copy JSON'}</span>
                  </button>
                </div>
                <pre className="p-3 rounded-xl bg-dark-800 border border-dark-700 font-mono text-xs text-indigo-300 overflow-x-auto max-h-60">
                  {JSON.stringify(selectedLog.metadata || {}, null, 2)}
                </pre>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setSelectedLog(null)}
                className="px-4 py-2 rounded-xl bg-dark-700 hover:bg-dark-600 text-slate-200 text-xs font-semibold"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
