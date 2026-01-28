/**
 * Type Definitions for Investigation Canvas UI
 * 
 * Defines all TypeScript interfaces for investigations, events, and related data structures.
 */

// Investigation Status enum
export type InvestigationStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED';

// Event Severity enum
export type EventSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';

// Event Source enum
export type EventSource = 'GIT' | 'CI' | 'LOGS' | 'METRICS' | 'TRACES' | 'MANUAL';

/**
 * Investigation Interface
 */
export interface Investigation {
  // Core fields
  id: string;
  title: string;
  description: string;
  service: string;
  environment?: string;

  // Status and severity
  status: InvestigationStatus;
  severity: EventSeverity;

  // Timing
  created_at: string;
  updated_at: string;
  estimated_mttr?: string;
  actual_mttr?: string;

  // Team and assignments
  assigned_to?: string;
  created_by: string;

  // Resolution
  root_cause?: string;
  resolution_summary?: string;

  // Metrics and automation
  automation_potential?: number;
  automation_notes?: string;
  business_impact?: string;
  impact_domain?: string;

  // Metadata
  metadata?: Record<string, any>;
  tags?: string[];
}

/**
 * Event Interface
 */
export interface Event {
  // Core fields
  id: string;
  investigation_id: string;
  message: string;
  timestamp: string;

  // Source and severity
  source: EventSource;
  severity: EventSeverity;

  // Context
  service?: string;
  environment?: string;

  // Tracing and correlation
  correlation_id?: string;
  trace_id?: string;
  request_id?: string;

  // Additional data
  metadata?: Record<string, any>;
  tags?: string[];
  context?: string;
}

/**
 * Connector Status Interface
 */
export interface ConnectorStatus {
  source: EventSource;
  state: 'CLOSED' | 'OPEN' | 'HALF_OPEN';
  failure_count: number;
  last_failure?: string;
  last_success?: string;
  dlq_size: number;
}

/**
 * API Response Interfaces
 */
export interface InvestigationListResponse {
  investigations: Investigation[];
  total_count: number;
  page: number;
  page_size: number;
}

export interface EventListResponse {
  events: Event[];
  total_count: number;
}

export interface ConnectorStatusResponse {
  connectors: ConnectorStatus[];
  timestamp: string;
}

/**
 * Component Props Interfaces
 */
export interface InvestigationCanvasProps {
  apiBaseUrl?: string;
}

export interface InvestigationListProps {
  onSelectInvestigation: (investigation: Investigation) => void;
  onRefresh?: () => void;
}

export interface InvestigationDetailProps {
  investigationId: string;
  onBack: () => void;
  onStatusChange?: (newStatus: InvestigationStatus) => void;
}

export interface EventTimelineProps {
  events: Event[];
  investigationId: string;
}

export interface ConnectorDashboardProps {
  connectors: ConnectorStatus[];
  onRefresh?: () => void;
}
