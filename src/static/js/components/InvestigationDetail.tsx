/**
 * InvestigationDetail Component
 * 
 * Displays detailed information about a single investigation including metadata,
 * status, team information, and associated events.
 * Features:
 * - Comprehensive investigation metadata
 * - Status and severity badges
 * - Team member assignments
 * - Investigation timeline
 * - MTTR estimation
 * - Edit/update capabilities
 */

import React, { useState, useEffect } from 'react';
import { Investigation, Event, InvestigationStatus, EventSeverity } from '../types';
import { API_BASE_URL } from '../config';
import EventTimeline from './EventTimeline';

interface InvestigationDetailProps {
  investigationId: string;
  onBack: () => void;
  onStatusChange?: (newStatus: InvestigationStatus) => void;
}

export const InvestigationDetail: React.FC<InvestigationDetailProps> = ({
  investigationId,
  onBack,
  onStatusChange,
}) => {
  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedInvestigation, setEditedInvestigation] = useState<Partial<Investigation>>({});

  // Fetch investigation details and related events
  useEffect(() => {
    const fetchDetails = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch investigation
        const invResponse = await fetch(`${API_BASE_URL}/api/investigations/${investigationId}`);
        if (!invResponse.ok) {
          throw new Error(`Failed to fetch investigation: ${invResponse.status}`);
        }
        const invData = await invResponse.json();
        setInvestigation(invData);
        setEditedInvestigation(invData);

        // Fetch related events
        const eventsResponse = await fetch(
          `${API_BASE_URL}/api/investigations/${investigationId}/events`
        );
        if (eventsResponse.ok) {
          const eventsData = await eventsResponse.json();
          setEvents(eventsData.events || []);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        console.error('Failed to fetch investigation details:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDetails();
  }, [investigationId]);

  const handleStatusChange = async (newStatus: InvestigationStatus) => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/investigations/${investigationId}/status`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: newStatus }),
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to update status: ${response.status}`);
      }

      setInvestigation((prev) => (prev ? { ...prev, status: newStatus } : null));
      onStatusChange?.(newStatus);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update status');
    }
  };

  const handleSave = async () => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/investigations/${investigationId}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(editedInvestigation),
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to update investigation: ${response.status}`);
      }

      const updated = await response.json();
      setInvestigation(updated);
      setIsEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save changes');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin text-4xl">⏳</div>
        <p className="ml-4 text-gray-600">Loading investigation details...</p>
      </div>
    );
  }

  if (!investigation) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-red-800 font-semibold">{error || 'Investigation not found'}</p>
        <button
          onClick={onBack}
          className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
        >
          ← Back
        </button>
      </div>
    );
  }

  const getSeverityColor = (severity: EventSeverity): string => {
    const colors: Record<EventSeverity, string> = {
      CRITICAL: 'bg-red-100 text-red-800 border-red-300',
      HIGH: 'bg-orange-100 text-orange-800 border-orange-300',
      MEDIUM: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      LOW: 'bg-green-100 text-green-800 border-green-300',
      INFO: 'bg-blue-100 text-blue-800 border-blue-300',
    };
    return colors[severity] || colors.INFO;
  };

  const getStatusColor = (status: InvestigationStatus): string => {
    const colors: Record<InvestigationStatus, string> = {
      OPEN: 'bg-red-100 text-red-800 border-red-300',
      IN_PROGRESS: 'bg-blue-100 text-blue-800 border-blue-300',
      RESOLVED: 'bg-green-100 text-green-800 border-green-300',
      CLOSED: 'bg-gray-100 text-gray-800 border-gray-300',
    };
    return colors[status] || colors.OPEN;
  };

  return (
    <div className="investigation-detail space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-start justify-between bg-white rounded-lg shadow p-6">
        <div className="flex-1">
          <button
            onClick={onBack}
            className="text-blue-600 hover:text-blue-800 font-semibold text-sm mb-4"
          >
            ← Back to List
          </button>

          {!isEditing ? (
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">{investigation.title}</h1>
              <p className="text-gray-600 text-sm font-mono">{investigation.id}</p>
            </div>
          ) : (
            <input
              type="text"
              value={editedInvestigation.title || ''}
              onChange={(e) =>
                setEditedInvestigation({ ...editedInvestigation, title: e.target.value })
              }
              className="text-3xl font-bold text-gray-900 w-full border-b-2 border-blue-500 focus:outline-none mb-2"
            />
          )}
        </div>

        <div className="flex gap-2">
          {isEditing ? (
            <>
              <button
                onClick={handleSave}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
              >
                ✓ Save
              </button>
              <button
                onClick={() => {
                  setEditedInvestigation(investigation);
                  setIsEditing(false);
                }}
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
              >
                ✕ Cancel
              </button>
            </>
          ) : (
            <button
              onClick={() => setIsEditing(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              ✎ Edit
            </button>
          )}
        </div>
      </div>

      {/* Status & Severity Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Status Card */}
        <div className="bg-white rounded-lg shadow p-6 space-y-4">
          <h2 className="text-lg font-bold text-gray-800">Status</h2>

          <div className={`px-4 py-3 rounded-lg border ${getStatusColor(investigation.status)}`}>
            <div className="flex items-center justify-between">
              <span className="text-lg font-semibold">{investigation.status}</span>
              {!isEditing && (
                <select
                  value={investigation.status}
                  onChange={(e) => handleStatusChange(e.target.value as InvestigationStatus)}
                  className="px-3 py-1 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="OPEN">Open</option>
                  <option value="IN_PROGRESS">In Progress</option>
                  <option value="RESOLVED">Resolved</option>
                  <option value="CLOSED">Closed</option>
                </select>
              )}
            </div>
          </div>

          {investigation.resolution_summary && (
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <p className="text-sm font-semibold text-gray-700 mb-2">Resolution Summary</p>
              <p className="text-gray-600 text-sm">{investigation.resolution_summary}</p>
            </div>
          )}
        </div>

        {/* Severity & Metadata Card */}
        <div className="bg-white rounded-lg shadow p-6 space-y-4">
          <h2 className="text-lg font-bold text-gray-800">Severity & Scope</h2>

          <div className={`px-4 py-3 rounded-lg border ${getSeverityColor(investigation.severity)}`}>
            <div className="text-lg font-semibold">{investigation.severity}</div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="bg-gray-50 p-3 rounded-lg">
              <p className="text-xs text-gray-600">Service</p>
              <p className="text-sm font-semibold text-gray-800">{investigation.service}</p>
            </div>
            <div className="bg-gray-50 p-3 rounded-lg">
              <p className="text-xs text-gray-600">Environment</p>
              <p className="text-sm font-semibold text-gray-800">{investigation.environment || 'N/A'}</p>
            </div>
            <div className="bg-gray-50 p-3 rounded-lg">
              <p className="text-xs text-gray-600">Created</p>
              <p className="text-sm font-semibold text-gray-800">
                {new Date(investigation.created_at).toLocaleDateString()}
              </p>
            </div>
            <div className="bg-gray-50 p-3 rounded-lg">
              <p className="text-xs text-gray-600">Estimated MTTR</p>
              <p className="text-sm font-semibold text-gray-800">{investigation.estimated_mttr || 'TBD'}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Description */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-bold text-gray-800 mb-4">Description</h2>
        {!isEditing ? (
          <p className="text-gray-700 whitespace-pre-wrap">{investigation.description}</p>
        ) : (
          <textarea
            value={editedInvestigation.description || ''}
            onChange={(e) =>
              setEditedInvestigation({ ...editedInvestigation, description: e.target.value })
            }
            className="w-full h-32 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
          />
        )}
      </div>

      {/* Event Timeline */}
      <div className="bg-white rounded-lg shadow p-6">
        <EventTimeline events={events} investigationId={investigationId} />
      </div>

      {/* Team & Automation */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Team Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold text-gray-800 mb-4">Team</h2>
          <div className="space-y-2">
            {investigation.assigned_to ? (
              <div className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg">
                <span className="text-2xl">👤</span>
                <span className="text-gray-800 font-semibold">{investigation.assigned_to}</span>
              </div>
            ) : (
              <p className="text-gray-500 text-sm">Not assigned</p>
            )}
          </div>
        </div>

        {/* Automation Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold text-gray-800 mb-4">Automation Potential</h2>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-2xl">⚙️</span>
              <span className="text-gray-800">
                {investigation.automation_potential
                  ? `${investigation.automation_potential}% automatable`
                  : 'Not assessed'}
              </span>
            </div>
            {investigation.automation_notes && (
              <p className="text-sm text-gray-600 mt-2">{investigation.automation_notes}</p>
            )}
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          <p className="font-semibold">Error</p>
          <p className="text-sm">{error}</p>
        </div>
      )}
    </div>
  );
};

export default InvestigationDetail;
