export interface User {
  id: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  created_at: string;
}

export interface Project {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  retention_days: number;
  created_at: string;
  updated_at: string;
}

export interface ApiKey {
  id: string;
  project_id: string;
  name: string;
  key_prefix: string;
  is_active: boolean;
  last_used_at?: string;
  created_at: string;
}

export interface ApiKeyCreated extends ApiKey {
  raw_key: string;
}

export interface LogItem {
  id: number;
  project_id: string;
  timestamp: string;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  message: string;
  metadata: Record<string, any>;
  created_at: string;
}

export interface LogListResponse {
  items: LogItem[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

export interface MetricPoint {
  bucket_time: string;
  min: number;
  max: number;
  avg: number;
  count: number;
}

export interface MetricQueryResponse {
  metric_name: string;
  bucket: string;
  points: MetricPoint[];
}

export interface MetricNameItem {
  name: string;
  count: number;
  last_seen: string;
}

export interface AlertRule {
  id: string;
  project_id: string;
  name: string;
  rule_type: 'error_count' | 'metric_threshold';
  target_metric?: string;
  condition_operator: '>' | '>=' | '<' | '<=';
  threshold: number;
  window_minutes: number;
  channel_type: 'email' | 'slack';
  channel_config: Record<string, any>;
  is_active: boolean;
  notification_cooldown_minutes: number;
  last_evaluated_at?: string;
  last_notified_at?: string;
  created_at: string;
}

export interface AlertEvent {
  id: string;
  rule_id: string;
  project_id: string;
  triggered_at: string;
  resolved_at?: string;
  status: 'triggered' | 'resolved';
  triggered_value: number;
  message: string;
  created_at: string;
}

export interface ErrorCluster {
  signature: string;
  component: string;
  count: number;
  severity: 'CRITICAL' | 'WARNING';
  sample_message: string;
  first_seen: string;
  last_seen: string;
}

export interface AIRecommendation {
  title: string;
  action: string;
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  rationale: string;
}

export interface AIHealthAnalysisResponse {
  project_id: string;
  timestamp: string;
  health_score: number;
  overall_status: 'healthy' | 'degraded' | 'critical';
  summary: string;
  total_errors_analyzed: number;
  error_clusters: ErrorCluster[];
  metric_anomalies: Array<{
    metric: string;
    condition: string;
    value: number;
    threshold: number;
    severity: string;
  }>;
  recommendations: AIRecommendation[];
}

