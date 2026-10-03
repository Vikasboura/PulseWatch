import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  AlertOctagon,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Terminal,
  Activity,
  Layers,
  Wrench,
  Clock,
} from 'lucide-react';
import { api } from '../api';
import { AIHealthAnalysisResponse } from '../types';

interface AIIncidentAnalystProps {
  projectId: string;
}

export const AIIncidentAnalyst: React.FC<AIIncidentAnalystProps> = ({ projectId }) => {
  const [data, setData] = useState<AIHealthAnalysisResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [windowMinutes, setWindowMinutes] = useState<number>(30);
  const [analyzing, setAnalyzing] = useState<boolean>(false);

  const loadInsights = async (mins: number = windowMinutes) => {
    try {
      setLoading(true);
      const res = await api.getAiInsights(projectId, mins);
      setData(res);
    } catch (err) {
      console.error('Failed to fetch AI insights:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerAnalysis = async () => {
    try {
      setAnalyzing(true);
      const res = await api.triggerAiAnalysis(projectId, windowMinutes);
      setData(res);
    } catch (err) {
      console.error('Failed to trigger AI analysis:', err);
    } finally {
      setAnalyzing(false);
    }
  };

  useEffect(() => {
    loadInsights(windowMinutes);
  }, [projectId, windowMinutes]);

  const getHealthBadge = (score: number, status: string) => {
    if (score >= 80) {
      return (
        <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
          <CheckCircle2 className="w-3.5 h-3.5" /> Nominal System Health ({score}/100)
        </span>
      );
    }
    if (score >= 50) {
      return (
        <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/30">
          <AlertTriangle className="w-3.5 h-3.5" /> Degraded Performance ({score}/100)
        </span>
      );
    }
    return (
      <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-rose-500/10 text-rose-400 border border-rose-500/30 animate-pulse">
        <AlertOctagon className="w-3.5 h-3.5" /> Incident Critical ({score}/100)
      </span>
    );
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-xl backdrop-blur-md relative overflow-hidden">
      {/* Decorative ambient gradient */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5 mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/30 shadow-inner">
            <Sparkles className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-slate-100 tracking-tight">
                AI Telemetry Copilot & Root Cause Analysis
              </h3>
              <span className="text-[10px] font-mono bg-cyan-950 text-cyan-400 border border-cyan-800/50 px-2 py-0.5 rounded font-semibold">
                NEURAL RCA
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Clusters error signatures, correlates time-series anomalies, and suggests runbook remediations.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <select
            value={windowMinutes}
            onChange={(e) => setWindowMinutes(Number(e.target.value))}
            className="bg-slate-800/80 border border-slate-700 text-xs font-mono text-slate-300 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-cyan-500"
          >
            <option value={15}>Past 15 Minutes</option>
            <option value={30}>Past 30 Minutes</option>
            <option value={60}>Past 1 Hour</option>
            <option value={360}>Past 6 Hours</option>
          </select>

          <button
            onClick={handleTriggerAnalysis}
            disabled={analyzing}
            className="flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-semibold px-3.5 py-1.5 rounded-lg text-xs transition-all shadow-md active:scale-95 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${analyzing ? 'animate-spin' : ''}`} />
            {analyzing ? 'Analyzing Telemetry...' : 'Trigger AI Diagnosis'}
          </button>
        </div>
      </div>

      {loading && !data ? (
        <div className="flex items-center justify-center py-16 gap-3 text-slate-400">
          <RefreshCw className="w-5 h-5 animate-spin text-cyan-400" />
          <span className="text-sm font-mono">Synthesizing telemetry data & clustering signatures...</span>
        </div>
      ) : data ? (
        <div className="space-y-6">
          {/* Executive Summary Card */}
          <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <span className="text-[11px] font-mono uppercase text-slate-500 tracking-wider">
                Telemetry Health Assessment
              </span>
              <p className="text-sm text-slate-200 font-medium leading-relaxed">{data.summary}</p>
            </div>
            <div className="shrink-0">{getHealthBadge(data.health_score, data.overall_status)}</div>
          </div>

          {/* Dual Columns: Error Clusters & AI Runbook Recommendations */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Clustered Error Signatures */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Layers className="w-4 h-4 text-slate-400" />
                  Clustered Error Signatures ({data.error_clusters.length})
                </h4>
                <span className="text-[11px] text-slate-400 font-mono">
                  {data.total_errors_analyzed} total errors
                </span>
              </div>

              {data.error_clusters.length === 0 ? (
                <div className="bg-slate-950/40 border border-slate-800/80 rounded-lg p-6 text-center text-xs text-slate-400">
                  No anomalous error clusters detected in this time window.
                </div>
              ) : (
                <div className="space-y-2.5 max-h-[360px] overflow-y-auto pr-1">
                  {data.error_clusters.map((cluster, i) => (
                    <div
                      key={i}
                      className="bg-slate-950/50 border border-slate-800/80 hover:border-slate-700/80 rounded-lg p-3.5 transition-all text-xs"
                    >
                      <div className="flex items-start justify-between gap-2 mb-1.5">
                        <span className="font-semibold text-slate-200">{cluster.signature}</span>
                        <div className="flex items-center gap-2">
                          <span className="bg-slate-800 text-slate-300 font-mono text-[10px] px-2 py-0.5 rounded font-bold">
                            {cluster.count}x
                          </span>
                          <span
                            className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                              cluster.severity === 'CRITICAL'
                                ? 'bg-rose-950 text-rose-400 border border-rose-800/60'
                                : 'bg-amber-950 text-amber-400 border border-amber-800/60'
                            }`}
                          >
                            {cluster.severity}
                          </span>
                        </div>
                      </div>

                      <div className="text-[11px] text-slate-400 font-mono mb-2">
                        Target Component: <span className="text-cyan-400">{cluster.component}</span>
                      </div>

                      <div className="bg-slate-900 border border-slate-800/90 rounded p-2 text-[11px] font-mono text-slate-300 truncate">
                        {cluster.sample_message}
                      </div>

                      <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono mt-2 pt-2 border-t border-slate-900">
                        <span>First: {new Date(cluster.first_seen).toLocaleTimeString()}</span>
                        <span>Latest: {new Date(cluster.last_seen).toLocaleTimeString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* AI Runbook Recommendations */}
            <div className="space-y-3">
              <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <Wrench className="w-4 h-4 text-cyan-400" />
                Actionable Remediation Runbooks ({data.recommendations.length})
              </h4>

              <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1">
                {data.recommendations.map((rec, i) => (
                  <div
                    key={i}
                    className="bg-slate-950/50 border border-slate-800/80 rounded-lg p-3.5 space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-slate-200">{rec.title}</span>
                      <span
                        className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                          rec.priority === 'CRITICAL'
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                            : rec.priority === 'HIGH'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                            : 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
                        }`}
                      >
                        {rec.priority} PRIORITY
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-400 leading-relaxed">{rec.rationale}</p>

                    <div className="bg-slate-900 border border-slate-800 rounded p-2 flex items-start gap-2 text-slate-300 font-mono text-[11px]">
                      <Terminal className="w-3.5 h-3.5 text-cyan-400 shrink-0 mt-0.5" />
                      <span>{rec.action}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
