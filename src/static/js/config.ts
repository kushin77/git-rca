/**
 * Application Configuration
 */

export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
export const API_TIMEOUT = 30000; // 30 seconds
export const PAGE_SIZE_DEFAULT = 10;

/**
 * Color Constants
 */
export const COLORS = {
  severity: {
    CRITICAL: '#dc2626',
    HIGH: '#ea580c',
    MEDIUM: '#eab308',
    LOW: '#16a34a',
    INFO: '#2563eb',
  },
  source: {
    GIT: '#ea580c',
    CI: '#2563eb',
    LOGS: '#a855f7',
    METRICS: '#16a34a',
    TRACES: '#eab308',
    MANUAL: '#6b7280',
  },
  status: {
    OPEN: '#dc2626',
    IN_PROGRESS: '#2563eb',
    RESOLVED: '#16a34a',
    CLOSED: '#9ca3af',
  },
};

/**
 * UI Constants
 */
export const PAGE_SIZE_OPTIONS = [5, 10, 20, 50, 100];
export const REFRESH_INTERVAL = 30000; // 30 seconds
