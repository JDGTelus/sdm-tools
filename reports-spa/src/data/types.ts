// TypeScript interfaces for SDM-Tools data structures

// Sprint Data Types
export interface SprintInfo {
  id: string
  name: string
  state: string
  start_date: string
  end_date: string
}

export interface DeveloperMetrics {
  name: string
  email: string
  commits_in_sprint: number
  issues_assigned_in_sprint: number
  issues_closed_in_sprint: number
  story_points_closed_in_sprint: number
}

export interface SprintAnalytics {
  sprint_info: SprintInfo
  developers: Record<string, DeveloperMetrics>
}

export interface TeamSprintData {
  generated_at: string
  sprint_analytics: Record<string, SprintAnalytics>
}

// Developer Activity Types
export interface ActivityBreakdown {
  issues_created: number
  issues_updated: number
  status_changes: number
  commits: number
}

export interface DeveloperActivity {
  email: string
  name: string
  jira_actions: number
  repo_actions: number
  breakdown: ActivityBreakdown
  total_activity: number
}

export interface ActivityPeriod {
  start: string
  end: string
}

export interface ActivitySummary {
  total_jira_actions: number
  total_repo_actions: number
  total_activity: number
  active_developers: number
  most_active_developer: string
}

export interface Last3DaysActivity {
  period: ActivityPeriod
  developers: DeveloperActivity[]
  summary: ActivitySummary
}

export interface DataPeriod {
  earliest: string
  latest: string
}

export interface Metadata {
  total_developers: number
  total_sprints: number
  active_sprint: string
  data_period: DataPeriod
}

export interface SprintActivityData {
  sprint_name: string
  developers: DeveloperActivity[]
  summary: ActivitySummary
}

export interface DeveloperSummary {
  email: string
  name: string
  total_sprints_participated: number
  total_commits: number
  total_jira_actions: number
  total_repo_actions: number
  avg_activity_per_sprint: number
  most_active_sprint?: string
}

export interface ActivityTrend {
  date: string
  total_activity: number
  jira_actions: number
  repo_actions: number
  active_developers: number
}

export interface DeveloperActivityData {
  generated_at: string
  metadata: Metadata
  last_3_days_activity: Last3DaysActivity
  sprint_activity: Record<string, SprintActivityData>
  developer_summary: DeveloperSummary[]
  activity_trends: ActivityTrend[]
}

// Global window interface for embedded data
declare global {
  interface Window {
    __SPRINT_DATA__?: TeamSprintData
    __ACTIVITY_DATA__?: DeveloperActivityData
    __DAILY_ACTIVITY_DATA__?: any
  }
}

export {}
