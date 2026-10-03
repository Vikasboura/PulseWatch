import {
  User,
  Project,
  ApiKey,
  ApiKeyCreated,
  LogListResponse,
  MetricQueryResponse,
  MetricNameItem,
  AlertRule,
  AlertEvent,
  AIHealthAnalysisResponse,
} from './types';

const API_BASE = '/api/v1';

export function getAuthToken(): string | null {
  return localStorage.getItem('pw_token');
}

export function setAuthToken(token: string) {
  localStorage.setItem('pw_token', token);
}

export function clearAuthToken() {
  localStorage.removeItem('pw_token');
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    if (res.status === 401) {
      clearAuthToken();
      window.dispatchEvent(new Event('auth-expired'));
    }
    const errBody = await res.json().catch(() => ({ detail: res.statusText }));
    const detailMsg =
      typeof errBody.detail === 'string'
        ? errBody.detail
        : Array.isArray(errBody.detail)
        ? errBody.detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ')
        : typeof errBody.detail === 'object'
        ? JSON.stringify(errBody.detail)
        : res.statusText || 'Request failed';
    throw new Error(detailMsg);
  }

  if (res.status === 204) {
    return null as T;
  }

  return res.json();
}

export const api = {
  // Auth
  register: (data: { email: string; password: string; full_name?: string }) =>
    request<User>('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  login: (data: { email: string; password: string }) =>
    request<{ access_token: string; token_type: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  getMe: () => request<User>('/auth/me'),

  // Projects
  listProjects: () => request<Project[]>('/projects'),
  createProject: (data: { name: string; description?: string; retention_days?: number }) =>
    request<Project>('/projects', { method: 'POST', body: JSON.stringify(data) }),
  deleteProject: (projectId: string) =>
    request<void>(`/projects/${projectId}`, { method: 'DELETE' }),

  // API Keys
  listApiKeys: (projectId: string) =>
    request<ApiKey[]>(`/projects/${projectId}/api-keys`),
  createApiKey: (projectId: string, name: string) =>
    request<ApiKeyCreated>(`/projects/${projectId}/api-keys`, {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),
  revokeApiKey: (projectId: string, keyId: string) =>
    request<void>(`/projects/${projectId}/api-keys/${keyId}`, { method: 'DELETE' }),

  // Logs
  getLogs: (
    projectId: string,
    params: { level?: string; search?: string; page?: number; limit?: number } = {}
  ) => {
    const q = new URLSearchParams();
    if (params.level) q.set('level', params.level);
    if (params.search) q.set('search', params.search);
    if (params.page) q.set('page', params.page.toString());
    if (params.limit) q.set('limit', params.limit.toString());
    return request<LogListResponse>(`/projects/${projectId}/logs?${q.toString()}`);
  },

  // Metrics
  getMetricNames: (projectId: string) =>
    request<MetricNameItem[]>(`/projects/${projectId}/metrics/names`),
  getMetrics: (
    projectId: string,
    name: string,
    bucket: '1m' | '5m' | '1h' | 'raw' = '5m'
  ) =>
    request<MetricQueryResponse>(
      `/projects/${projectId}/metrics?name=${encodeURIComponent(name)}&bucket=${bucket}`
    ),

  // Alerts
  listRules: (projectId: string) =>
    request<AlertRule[]>(`/projects/${projectId}/alerts/rules`),
  createRule: (projectId: string, rule: Partial<AlertRule>) =>
    request<AlertRule>(`/projects/${projectId}/alerts/rules`, {
      method: 'POST',
      body: JSON.stringify(rule),
    }),
  deleteRule: (projectId: string, ruleId: string) =>
    request<void>(`/projects/${projectId}/alerts/rules/${ruleId}`, { method: 'DELETE' }),
  listEvents: (projectId: string) =>
    request<AlertEvent[]>(`/projects/${projectId}/alerts/events`),
  evaluateNow: (projectId: string) =>
    request<{ status: string; rules_evaluated: number; events_affected: any[] }>(
      `/projects/${projectId}/alerts/evaluate`,
      { method: 'POST' }
    ),
  // AI Telemetry Intelligence
  getAiInsights: (projectId: string, windowMinutes: number = 30) =>
    request<AIHealthAnalysisResponse>(`/projects/${projectId}/ai/insights?window_minutes=${windowMinutes}`),
  triggerAiAnalysis: (projectId: string, windowMinutes: number = 30) =>
    request<AIHealthAnalysisResponse>(`/projects/${projectId}/ai/analyze?window_minutes=${windowMinutes}`, {
      method: 'POST',
    }),
};
