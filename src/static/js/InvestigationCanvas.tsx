/**
 * InvestigationCanvas Component
 * 
 * Main container component that orchestrates the investigation visualization.
 * Features:
 * - Investigation list with filtering and search
 * - Investigation detail view
 * - Event timeline visualization
 * - Connector health dashboard
 * - Multi-view layout (list → detail)
 */

import React, { useState, useEffect } from 'react';
import InvestigationList from './components/InvestigationList';
import InvestigationDetail from './components/InvestigationDetail';
import EventTimeline from './components/EventTimeline';
import { Investigation, ConnectorStatus } from './types';
import { API_BASE_URL, REFRESH_INTERVAL } from './config';

type ViewMode = 'list' | 'detail';

interface InvestigationCanvasProps {
  apiBaseUrl?: string;
}

export const InvestigationCanvas: React.FC<InvestigationCanvasProps> = ({ apiBaseUrl }) => {
  const api = apiBaseUrl || API_BASE_URL;

  // View state
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [selectedInvestigation, setSelectedInvestigation] = useState<Investigation | null>(null);

  // Connector status state
  const [connectorStatuses, setConnectorStatuses] = useState<ConnectorStatus[]>([]);
  const [connectorStatusLoading, setConnectorStatusLoading] = useState(true);

  // Fetch connector statuses
  useEffect(() => {
    const fetchConnectorStatus = async () => {
      try {
        setConnectorStatusLoading(true);
        const response = await fetch(`${api}/api/connectors/status`);
        if (response.ok) {
          const data = await response.json();
          setConnectorStatuses(data.connectors || []);
        }
      } catch (err) {
        console.error('Failed to fetch connector status:', err);
      } finally {
        setConnectorStatusLoading(false);
      }
    };

    fetchConnectorStatus();

    // Set up auto-refresh
    const interval = setInterval(fetchConnectorStatus, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [api]);

  const handleSelectInvestigation = (investigation: Investigation) => {
    setSelectedInvestigation(investigation);
    setViewMode('detail');
  };

  const handleBackToList = () => {
    setViewMode('list');
    setSelectedInvestigation(null);
  };

  const getConnectorStateColor = (state: string): string => {
    const colors: Record<string, string> = {
      CLOSED: 'bg-green-100 text-green-800 border-green-300',
      OPEN: 'bg-red-100 text-red-800 border-red-300',
      HALF_OPEN: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    };
    return colors[state] || colors.CLOSED;
  };

  const getConnectorIcon = (source: string): string => {
    const icons: Record<string, string> = {
      GIT: '🔗',
      CI: '⚙️',
      LOGS: '📝',
      METRICS: '📊',
      TRACES: '🔍',
      MANUAL: '✏️',
    };
    return icons[source] || '📌';
  };

  return (
    <div className="investigation-canvas min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold text-gray-900">🔍 Investigation Canvas</h1>
            <span className="text-gray-600 text-sm">Root Cause Analysis Dashboard</span>
          </div>
          <div className="flex items-center gap-4">
            {viewMode === 'detail' && selectedInvestigation && (
              <span className="text-sm text-gray-700">
                <span className="font-semibold">{selectedInvestigation.service}</span>
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-6">
        {viewMode === 'list' ? (
          <div className="space-y-6">
            {/* Connector Health Dashboard */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-bold text-gray-800 mb-4">📡 Connector Health</h2>

              {connectorStatusLoading ? (
                <p className="text-gray-600">Loading connector status...</p>
              ) : connectorStatuses.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {connectorStatuses.map((connector) => (
                    <div
                      key={connector.source}
                      className={`p-4 rounded-lg border ${getConnectorStateColor(connector.state)}`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-2xl">{getConnectorIcon(connector.source)}</span>
                          <span className="font-semibold">{connector.source}</span>
                        </div>
                        <span className="text-xs font-bold">{connector.state}</span>
                      </div>

                      <div className="text-sm space-y-1">
                        <div className="flex justify-between">
                          <span>Failures:</span>
                          <span className="font-mono">{connector.failure_count}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>DLQ Size:</span>
                          <span className="font-mono">{connector.dlq_size}</span>
                        </div>
                        {connector.last_success && (
                          <div className="flex justify-between text-xs text-gray-600">
                            <span>Last Success:</span>
                            <span>
                              {new Date(connector.last_success).toLocaleTimeString()}
                            </span>
                          </div>
                        )}
                      </div>

                      {connector.dlq_size > 0 && (
                        <button className="mt-3 w-full px-3 py-1 bg-orange-600 text-white text-xs rounded hover:bg-orange-700 transition">
                          🔄 Replay DLQ ({connector.dlq_size})
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500">No connector status available</p>
              )}
            </div>

            {/* Investigation List */}
            <InvestigationList onSelectInvestigation={handleSelectInvestigation} />
          </div>
        ) : selectedInvestigation ? (
          <InvestigationDetail
            investigationId={selectedInvestigation.id}
            onBack={handleBackToList}
          />
        ) : null}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-6 py-6 text-center text-sm text-gray-600">
          <p>Git RCA Workspace © 2024 | Investigation Canvas v1.0</p>
        </div>
      </footer>
    </div>
  );
};

export default InvestigationCanvas;
