import React, { useState, useEffect } from 'react';
import {
  Activity,
  Layers,
  Clock,
  TrendingUp,
  RefreshCw,
  BarChart2,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Project, MetricNameItem, MetricPoint } from '../types';
import { api } from '../api';

interface MetricsPageProps {
  project: Project;
}

export const MetricsPage: React.FC<MetricsPageProps> = ({ project }) => {
  const [metricNames, setMetricNames] = useState<MetricNameItem[]>([]);
  const [selectedMetric, setSelectedMetric] = useState<string>('');
  const [bucket, setBucket] = useState<'1m' | '5m' | '1h' | 'raw'>('5m');
  const [points, setPoints] = useState<MetricPoint[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadNames();
  }, [project.id]);

  useEffect(() => {
    if (selectedMetric) {
      loadMetricData();
    }
  }, [selectedMetric, bucket, project.id]);

  const loadNames = async () => {
    try {
      const names = await api.getMetricNames(project.id);
      setMetricNames(names);
      if (names.length > 0 && !selectedMetric) {
        setSelectedMetric(names[0].name);
      }
    } catch (e) {
      console.error('Failed to load metric names', e);
    }
  };

  const loadMetricData = async () => {
    if (!selectedMetric) return;
    setLoading(true);
    try {
      const resp = await api.getMetrics(project.id, selectedMetric, bucket);
      setPoints(resp.points);
    } catch (e) {
      console.error('Failed to load metric data', e);
    } finally {
      setLoading(false);
    }
  };

  // Compute stat highlights
  const avgVal = points.length > 0 ? (points.reduce((a, b) => a + b.avg, 0) / points.length).toFixed(2) : '0';
  const maxVal = points.length > 0 ? Math.max(...points.map((p) => p.max)).toFixed(2) : '0';
  const minVal = points.length > 0 ? Math.min(...points.map((p) => p.min)).toFixed(2) : '0';

  const chartFormattedData = points.map((p) => {
    const d = new Date(p.bucket_time);
    return {
      time: `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`,
      avg: p.avg,
      min: p.min,
      max: p.max,
      count: p.count,
    };
  });

  return (
    <div className="space-y-6">
      {/* Selector Bar */}
      <div className="glow-card rounded-2xl p-5 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400">
            <BarChart2 className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white">Time-Series Metric Explorer</h2>
            <p className="text-xs text-slate-400">Aggregated metric trends across custom time buckets</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* Metric Dropdown */}
          <select
            value={selectedMetric}
            onChange={(e) => setSelectedMetric(e.target.value)}
            className="px-3.5 py-2 rounded-xl bg-dark-800 border border-dark-600 focus:border-indigo-500 focus:outline-none text-slate-200 text-xs font-semibold"
          >
            {metricNames.length === 0 && <option value="">No metrics recorded yet</option>}
            {metricNames.map((m) => (
              <option key={m.name} value={m.name}>
                {m.name} ({m.count} pts)
              </option>
            ))}
          </select>

          {/* Time Bucket Selector */}
          <div className="flex items-center space-x-1 bg-dark-800 p-1 rounded-xl border border-dark-600 text-xs font-semibold">
            {(['1m', '5m', '1h', 'raw'] as const).map((b) => (
              <button
                key={b}
                onClick={() => setBucket(b)}
                className={`px-3 py-1.5 rounded-lg uppercase transition ${
                  bucket === b ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {b}
              </button>
            ))}
          </div>

          <button
            onClick={loadMetricData}
            title="Refresh metric query"
            className="p-2 rounded-xl bg-dark-800 hover:bg-dark-700 text-slate-400 hover:text-white border border-dark-600 transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Summary KPI Badges */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="glow-card rounded-2xl p-4">
          <div className="text-xs text-slate-400 font-semibold uppercase">Average Value</div>
          <div className="text-2xl font-extrabold text-white mt-1">{avgVal}</div>
        </div>
        <div className="glow-card rounded-2xl p-4">
          <div className="text-xs text-slate-400 font-semibold uppercase">Peak (Max)</div>
          <div className="text-2xl font-extrabold text-rose-400 mt-1">{maxVal}</div>
        </div>
        <div className="glow-card rounded-2xl p-4">
          <div className="text-xs text-slate-400 font-semibold uppercase">Lowest (Min)</div>
          <div className="text-2xl font-extrabold text-emerald-400 mt-1">{minVal}</div>
        </div>
      </div>

      {/* Recharts Area Chart */}
      <div className="glow-card rounded-2xl p-6 shadow-xl">
        <div className="mb-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
            {selectedMetric ? `metric:${selectedMetric} [bucket: ${bucket}]` : 'Select a metric'}
          </h3>
        </div>

        <div className="h-80 w-full">
          {chartFormattedData.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs">
              <Activity className="w-8 h-8 text-slate-600 mb-2" />
              <span>No metric points recorded for the selected range.</span>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartFormattedData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorMetricAvg" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366F1" stopOpacity={0.5} />
                    <stop offset="95%" stopColor="#6366F1" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" stroke="#4B5563" fontSize={11} tickLine={false} />
                <YAxis stroke="#4B5563" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '12px', fontSize: '12px' }}
                />
                <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                <Area type="monotone" dataKey="avg" name="Average" stroke="#6366F1" fill="url(#colorMetricAvg)" strokeWidth={2} />
                <Area type="monotone" dataKey="max" name="Peak (Max)" stroke="#F43F5E" fill="none" strokeDasharray="3 3" />
                <Area type="monotone" dataKey="min" name="Min" stroke="#10B981" fill="none" strokeDasharray="3 3" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
};
