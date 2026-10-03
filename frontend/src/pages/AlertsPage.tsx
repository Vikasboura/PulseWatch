import React, { useState, useEffect } from 'react';
import {
  Bell,
  Plus,
  Trash2,
  PlayCircle,
  ShieldCheck,
  ShieldAlert,
  Clock,
  MessageSquare,
  Mail,
  CheckCircle,
  X,
} from 'lucide-react';
import { Project, AlertRule, AlertEvent } from '../types';
import { api } from '../api';

interface AlertsPageProps {
  project: Project;
}

export const AlertsPage: React.FC<AlertsPageProps> = ({ project }) => {
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [events, setEvents] = useState<AlertEvent[]>([]);
  const [activeTab, setActiveTab] = useState<'rules' | 'history'>('rules');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [evalMessage, setEvalMessage] = useState('');

  // Form state
  const [name, setName] = useState('');
  const [ruleType, setRuleType] = useState<'error_count' | 'metric_threshold'>('error_count');
  const [targetMetric, setTargetMetric] = useState('');
  const [operator, setOperator] = useState<'>' | '>=' | '<' | '<='>('>');
  const [threshold, setThreshold] = useState<number>(10);
  const [windowMinutes, setWindowMinutes] = useState<number>(5);
  const [channelType, setChannelType] = useState<'slack' | 'email'>('slack');
  const [channelDestination, setChannelDestination] = useState('');
  const [cooldown, setCooldown] = useState<number>(15);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, [project.id]);

  const loadData = async () => {
    try {
      const [r, e] = await Promise.all([
        api.listRules(project.id),
        api.listEvents(project.id),
      ]);
      setRules(r);
      setEvents(e);
    } catch (err) {
      console.error('Failed to load alert info', err);
    }
  };

  const handleCreateRule = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const channel_config =
        channelType === 'slack'
          ? { webhook_url: channelDestination.trim() }
          : { email: channelDestination.trim() };

      await api.createRule(project.id, {
        name: name.trim(),
        rule_type: ruleType,
        target_metric: ruleType === 'metric_threshold' ? targetMetric.trim() : undefined,
        condition_operator: operator,
        threshold: Number(threshold),
        window_minutes: Number(windowMinutes),
        channel_type: channelType,
        channel_config,
        notification_cooldown_minutes: Number(cooldown),
      });

      setIsModalOpen(false);
      resetForm();
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to create rule');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setName('');
    setRuleType('error_count');
    setTargetMetric('');
    setThreshold(10);
    setChannelDestination('');
  };

  const handleDeleteRule = async (ruleId: string) => {
    if (!confirm('Are you sure you want to delete this alert rule?')) return;
    try {
      await api.deleteRule(project.id, ruleId);
      setRules(rules.filter((r) => r.id !== ruleId));
    } catch (err: any) {
      alert(err.message || 'Failed to delete rule');
    }
  };

  const handleEvaluateNow = async () => {
    setEvaluating(true);
    setEvalMessage('');
    try {
      const res = await api.evaluateNow(project.id);
      setEvalMessage(`Evaluated ${res.rules_evaluated} rules. Incidents updated: ${res.events_affected.length}`);
      await loadData();
      setTimeout(() => setEvalMessage(''), 4000);
    } catch (err: any) {
      setEvalMessage(`Evaluation failed: ${err.message}`);
    } finally {
      setEvaluating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="glow-card rounded-2xl p-5 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400">
            <Bell className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white">Alert Rules & Incidents</h2>
            <p className="text-xs text-slate-400">Automated threshold triggers, cooldown dedup, and incident management</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleEvaluateNow}
            disabled={evaluating}
            className="flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-dark-800 hover:bg-dark-700 border border-dark-600 text-slate-200 text-xs font-semibold transition"
          >
            <PlayCircle className={`w-4 h-4 text-emerald-400 ${evaluating ? 'animate-spin' : ''}`} />
            <span>{evaluating ? 'Evaluating...' : 'Evaluate Now'}</span>
          </button>

          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 transition"
          >
            <Plus className="w-4 h-4" />
            <span>Create Rule</span>
          </button>
        </div>
      </div>

      {evalMessage && (
        <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-mono">
          {evalMessage}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-dark-700 space-x-6 text-sm font-semibold">
        <button
          onClick={() => setActiveTab('rules')}
          className={`pb-3 transition ${
            activeTab === 'rules'
              ? 'text-indigo-400 border-b-2 border-indigo-500'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Active Rules ({rules.length})
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`pb-3 transition ${
            activeTab === 'history'
              ? 'text-indigo-400 border-b-2 border-indigo-500'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Incident History ({events.length})
        </button>
      </div>

      {/* Active Rules View */}
      {activeTab === 'rules' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {rules.map((rule) => (
            <div key={rule.id} className="glow-card rounded-2xl p-5 shadow-lg flex flex-col justify-between space-y-4">
              <div>
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                    <span className="font-bold text-white text-sm">{rule.name}</span>
                  </div>
                  <button
                    onClick={() => handleDeleteRule(rule.id)}
                    className="p-1.5 rounded-lg hover:bg-rose-500/10 text-slate-500 hover:text-rose-400 transition"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                <div className="mt-3 p-3 rounded-xl bg-dark-800 border border-dark-700 font-mono text-xs text-indigo-300">
                  IF {rule.rule_type === 'error_count' ? 'error_count' : rule.target_metric}{' '}
                  {rule.condition_operator} {rule.threshold} in rolling {rule.window_minutes}m window
                </div>

                <div className="mt-4 flex items-center space-x-4 text-xs text-slate-400">
                  <div className="flex items-center space-x-1.5">
                    {rule.channel_type === 'slack' ? (
                      <MessageSquare className="w-4 h-4 text-amber-400" />
                    ) : (
                      <Mail className="w-4 h-4 text-indigo-400" />
                    )}
                    <span className="capitalize">{rule.channel_type}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Clock className="w-3.5 h-3.5 text-slate-500" />
                    <span>Cooldown: {rule.notification_cooldown_minutes}m</span>
                  </div>
                </div>
              </div>

              {rule.last_notified_at && (
                <div className="text-[11px] text-slate-500 border-t border-dark-700/60 pt-2">
                  Last notified: {new Date(rule.last_notified_at).toLocaleString()}
                </div>
              )}
            </div>
          ))}

          {rules.length === 0 && (
            <div className="col-span-full glow-card rounded-2xl p-12 text-center text-slate-500 text-xs">
              No alert rules created yet. Click "Create Rule" above to define automated alerting thresholds.
            </div>
          )}
        </div>
      )}

      {/* Incident History View */}
      {activeTab === 'history' && (
        <div className="glow-card rounded-2xl border border-dark-700 shadow-xl overflow-hidden">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-dark-800 text-slate-400 border-b border-dark-700 text-[11px] uppercase tracking-wider">
              <tr>
                <th className="px-5 py-3 font-semibold">Status</th>
                <th className="px-5 py-3 font-semibold">Triggered Value</th>
                <th className="px-5 py-3 font-semibold">Details</th>
                <th className="px-5 py-3 font-semibold">Triggered At</th>
                <th className="px-5 py-3 font-semibold">Resolved At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-700/60">
              {events.map((ev) => (
                <tr key={ev.id} className="hover:bg-dark-800/50 transition">
                  <td className="px-5 py-3.5">
                    <span
                      className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold border uppercase ${
                        ev.status === 'triggered'
                          ? 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                          : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                      }`}
                    >
                      {ev.status === 'triggered' ? (
                        <ShieldAlert className="w-3 h-3" />
                      ) : (
                        <CheckCircle className="w-3 h-3" />
                      )}
                      <span>{ev.status}</span>
                    </span>
                  </td>
                  <td className="px-5 py-3.5 font-bold text-white">{ev.triggered_value}</td>
                  <td className="px-5 py-3.5 text-slate-300 max-w-xs truncate">{ev.message}</td>
                  <td className="px-5 py-3.5 text-slate-400">{new Date(ev.triggered_at).toLocaleString()}</td>
                  <td className="px-5 py-3.5 text-slate-400">
                    {ev.resolved_at ? new Date(ev.resolved_at).toLocaleString() : '—'}
                  </td>
                </tr>
              ))}
              {events.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center py-12 text-slate-500">
                    No alert incident events recorded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Rule Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glow-card w-full max-w-lg rounded-2xl p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-4 border-b border-dark-700">
              <div className="flex items-center space-x-2 text-white font-bold text-lg">
                <Bell className="w-5 h-5 text-indigo-400" />
                <span>Configure Alert Rule</span>
              </div>
              <button onClick={() => setIsModalOpen(false)} className="p-1 rounded-lg text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateRule} className="mt-4 space-y-4 text-xs">
              <div>
                <label className="block uppercase font-semibold text-slate-400 mb-1.5">Rule Name *</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Critical Error Surge"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-dark-800 border border-dark-600 focus:border-indigo-500 focus:outline-none text-slate-100 text-sm"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block uppercase font-semibold text-slate-400 mb-1.5">Rule Type</label>
                  <select
                    value={ruleType}
                    onChange={(e) => setRuleType(e.target.value as any)}
                    className="w-full px-3 py-2.5 rounded-xl bg-dark-800 border border-dark-600 text-slate-100 font-semibold"
                  >
                    <option value="error_count">Error Count</option>
                    <option value="metric_threshold">Metric Threshold</option>
                  </select>
                </div>

                {ruleType === 'metric_threshold' && (
                  <div>
                    <label className="block uppercase font-semibold text-slate-400 mb-1.5">Target Metric Name *</label>
                    <input
                      type="text"
                      required
                      value={targetMetric}
                      onChange={(e) => setTargetMetric(e.target.value)}
                      placeholder="e.g. http_latency_ms"
                      className="w-full px-3 py-2.5 rounded-xl bg-dark-800 border border-dark-600 text-slate-100"
                    />
                  </div>
                )}
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block uppercase font-semibold text-slate-400 mb-1.5">Condition</label>
                  <select
                    value={operator}
                    onChange={(e) => setOperator(e.target.value as any)}
                    className="w-full px-3 py-2.5 rounded-xl bg-dark-800 border border-dark-600 text-slate-100 font-semibold"
                  >
                    <option value=">">&gt; (Greater than)</option>
                    <option value=">=">&gt;= (Greater or equal)</option>
                    <option value="<">&lt; (Less than)</option>
                    <option value="<=">&lt;= (Less or equal)</option>
                  </select>
                </div>

                <div>
                  <label className="block uppercase font-semibold text-slate-400 mb-1.5">Threshold *</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={threshold}
                    onChange={(e) => setThreshold(Number(e.target.value))}
                    className="w-full px-3 py-2.5 rounded-xl bg-dark-800 border border-dark-600 text-slate-100"
                  />
                </div>

                <div>
                  <label className="block uppercase font-semibold text-slate-400 mb-1.5">Window (Mins)</label>
                  <input
                    type="number"
                    min={1}
                    max={1440}
                    value={windowMinutes}
                    onChange={(e) => setWindowMinutes(Number(e.target.value))}
                    className="w-full px-3 py-2.5 rounded-xl bg-dark-800 border border-dark-600 text-slate-100"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block uppercase font-semibold text-slate-400 mb-1.5">Channel</label>
                  <select
                    value={channelType}
                    onChange={(e) => setChannelType(e.target.value as any)}
                    className="w-full px-3 py-2.5 rounded-xl bg-dark-800 border border-dark-600 text-slate-100 font-semibold"
                  >
                    <option value="slack">Slack Webhook</option>
                    <option value="email">Email</option>
                  </select>
                </div>

                <div>
                  <label className="block uppercase font-semibold text-slate-400 mb-1.5">Cooldown (Mins)</label>
                  <input
                    type="number"
                    min={1}
                    value={cooldown}
                    onChange={(e) => setCooldown(Number(e.target.value))}
                    className="w-full px-3 py-2.5 rounded-xl bg-dark-800 border border-dark-600 text-slate-100"
                  />
                </div>
              </div>

              <div>
                <label className="block uppercase font-semibold text-slate-400 mb-1.5">
                  {channelType === 'slack' ? 'Slack Webhook URL *' : 'Alert Recipient Email *'}
                </label>
                <input
                  type="text"
                  required
                  value={channelDestination}
                  onChange={(e) => setChannelDestination(e.target.value)}
                  placeholder={channelType === 'slack' ? 'https://hooks.slack.com/services/...' : 'alerts@company.com'}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-dark-800 border border-dark-600 text-slate-100 text-sm"
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
                  disabled={loading}
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition shadow-lg shadow-indigo-600/30"
                >
                  {loading ? 'Saving...' : 'Save Alert Rule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
