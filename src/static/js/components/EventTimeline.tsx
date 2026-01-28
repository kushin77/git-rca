/**
 * EventTimeline Component
 * 
 * Displays events in chronological order with visual indicators for event source and severity.
 * Features:
 * - Timeline visualization with events sorted by timestamp
 * - Color-coded event sources (Git, CI, Logs, Metrics, Traces, Manual)
 * - Severity indicators with visual hierarchy
 * - Event details on hover/expand
 * - Filter by event source
 */

import React, { useState, useMemo } from 'react';
import { Event, EventSource, EventSeverity } from '../types';

interface EventTimelineProps {
  events: Event[];
  investigationId: string;
}

type SourceFilter = EventSource | 'all';

export const EventTimeline: React.FC<EventTimelineProps> = ({ events, investigationId }) => {
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const [selectedSource, setSelectedSource] = useState<SourceFilter>('all');

  // Filter events by selected source
  const filteredEvents = useMemo(() => {
    return events
      .filter((e) => selectedSource === 'all' || e.source === selectedSource)
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  }, [events, selectedSource]);

  // Count events by source
  const sourceCount = useMemo(() => {
    const counts: Partial<Record<EventSource, number>> = {};
    events.forEach((e) => {
      counts[e.source] = (counts[e.source] || 0) + 1;
    });
    return counts;
  }, [events]);

  const getSourceColor = (source: EventSource): string => {
    const colors: Record<EventSource, string> = {
      GIT: 'bg-orange-100 text-orange-800 border-orange-300',
      CI: 'bg-blue-100 text-blue-800 border-blue-300',
      LOGS: 'bg-purple-100 text-purple-800 border-purple-300',
      METRICS: 'bg-green-100 text-green-800 border-green-300',
      TRACES: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      MANUAL: 'bg-gray-100 text-gray-800 border-gray-300',
    };
    return colors[source] || colors.MANUAL;
  };

  const getSourceIcon = (source: EventSource): string => {
    const icons: Record<EventSource, string> = {
      GIT: '🔗',
      CI: '⚙️',
      LOGS: '📝',
      METRICS: '📊',
      TRACES: '🔍',
      MANUAL: '✏️',
    };
    return icons[source] || '📌';
  };

  const getSeverityColor = (severity: EventSeverity): string => {
    const colors: Record<EventSeverity, string> = {
      CRITICAL: 'border-red-500 bg-red-50',
      HIGH: 'border-orange-500 bg-orange-50',
      MEDIUM: 'border-yellow-500 bg-yellow-50',
      LOW: 'border-green-500 bg-green-50',
      INFO: 'border-blue-500 bg-blue-50',
    };
    return colors[severity] || colors.INFO;
  };

  const getSeverityBadgeColor = (severity: EventSeverity): string => {
    const colors: Record<EventSeverity, string> = {
      CRITICAL: 'bg-red-100 text-red-800',
      HIGH: 'bg-orange-100 text-orange-800',
      MEDIUM: 'bg-yellow-100 text-yellow-800',
      LOW: 'bg-green-100 text-green-800',
      INFO: 'bg-blue-100 text-blue-800',
    };
    return colors[severity] || colors.INFO;
  };

  const formatTime = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  return (
    <div className="event-timeline space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-bold text-gray-800">Event Timeline</h3>
        <span className="text-sm text-gray-600">{filteredEvents.length} events</span>
      </div>

      {/* Source Filter Chips */}
      <div className="flex gap-2 flex-wrap pb-4 border-b">
        <button
          onClick={() => setSelectedSource('all')}
          className={`px-3 py-1 rounded-full text-sm font-semibold transition ${
            selectedSource === 'all'
              ? 'bg-gray-800 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          All ({events.length})
        </button>

        {(Object.keys(sourceCount) as EventSource[]).map((source) => (
          <button
            key={source}
            onClick={() => setSelectedSource(source)}
            className={`px-3 py-1 rounded-full text-sm font-semibold transition border ${
              selectedSource === source ? getSourceColor(source) : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {getSourceIcon(source)} {source} ({sourceCount[source] || 0})
          </button>
        ))}
      </div>

      {/* Timeline Events */}
      <div className="space-y-3">
        {filteredEvents.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p>No events found for selected filter</p>
          </div>
        ) : (
          filteredEvents.map((event, index) => (
            <div
              key={`${event.id}-${index}`}
              className={`border-l-4 p-4 rounded-lg cursor-pointer transition hover:shadow-md ${getSeverityColor(
                event.severity
              )}`}
              onClick={() => setExpandedEventId(expandedEventId === event.id ? null : event.id)}
            >
              {/* Event Header */}
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-2xl">{getSourceIcon(event.source)}</span>
                    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${getSourceColor(event.source)}`}>
                      {event.source}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${getSeverityBadgeColor(event.severity)}`}>
                      {event.severity}
                    </span>
                  </div>
                  <p className="text-sm font-semibold text-gray-800 mb-1">{event.message}</p>
                  <p className="text-xs text-gray-600">{formatTime(event.timestamp)}</p>
                </div>
                <span className="text-lg text-gray-400">{expandedEventId === event.id ? '▼' : '▶'}</span>
              </div>

              {/* Expanded Details */}
              {expandedEventId === event.id && (
                <div className="mt-4 pt-4 border-t space-y-3">
                  {/* Metadata */}
                  {event.metadata && Object.keys(event.metadata).length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-gray-700 mb-2">Metadata</h4>
                      <div className="grid grid-cols-2 gap-2">
                        {Object.entries(event.metadata).map(([key, value]) => (
                          <div key={key} className="bg-white bg-opacity-50 p-2 rounded text-xs">
                            <span className="font-semibold text-gray-700">{key}:</span>
                            <span className="text-gray-600 ml-1">{String(value)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Tags */}
                  {event.tags && event.tags.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-gray-700 mb-2">Tags</h4>
                      <div className="flex gap-1 flex-wrap">
                        {event.tags.map((tag, i) => (
                          <span key={i} className="bg-gray-300 text-gray-700 px-2 py-1 rounded text-xs">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Service and Correlation */}
                  {(event.service || event.correlation_id) && (
                    <div className="bg-white bg-opacity-50 p-3 rounded text-xs space-y-1">
                      {event.service && (
                        <div>
                          <span className="font-semibold text-gray-700">Service:</span>
                          <span className="text-gray-600 ml-1 font-mono">{event.service}</span>
                        </div>
                      )}
                      {event.correlation_id && (
                        <div>
                          <span className="font-semibold text-gray-700">Correlation ID:</span>
                          <span className="text-gray-600 ml-1 font-mono">{event.correlation_id}</span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Raw JSON Toggle */}
                  <details className="text-xs">
                    <summary className="font-semibold text-gray-700 cursor-pointer">Raw JSON</summary>
                    <pre className="mt-2 bg-gray-800 text-gray-100 p-2 rounded overflow-auto text-xs">
                      {JSON.stringify(event, null, 2)}
                    </pre>
                  </details>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Summary Stats */}
      {filteredEvents.length > 0 && (
        <div className="bg-gray-50 rounded-lg p-4 mt-6">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Timeline Statistics</h4>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-600">First Event</p>
              <p className="text-sm font-semibold text-gray-800">
                {formatTime(filteredEvents[filteredEvents.length - 1].timestamp)}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-600">Last Event</p>
              <p className="text-sm font-semibold text-gray-800">
                {formatTime(filteredEvents[0].timestamp)}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-600">Duration</p>
              <p className="text-sm font-semibold text-gray-800">
                {(() => {
                  const start = new Date(filteredEvents[filteredEvents.length - 1].timestamp);
                  const end = new Date(filteredEvents[0].timestamp);
                  const diffMs = end.getTime() - start.getTime();
                  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
                  const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
                  return diffHours > 0 ? `${diffHours}h ${diffMins}m` : `${diffMins}m`;
                })()}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-600">Events/Hour</p>
              <p className="text-sm font-semibold text-gray-800">
                {(() => {
                  const start = new Date(filteredEvents[filteredEvents.length - 1].timestamp);
                  const end = new Date(filteredEvents[0].timestamp);
                  const diffHours = (end.getTime() - start.getTime()) / (1000 * 60 * 60);
                  return diffHours > 0 ? (filteredEvents.length / diffHours).toFixed(1) : filteredEvents.length;
                })()}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EventTimeline;
