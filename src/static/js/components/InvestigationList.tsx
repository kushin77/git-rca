/**
 * InvestigationList Component
 * 
 * Displays a paginated list of investigations with filtering, search, and sorting capabilities.
 * Features:
 * - Search by investigation ID, service, title
 * - Filter by status (Open, In Progress, Resolved, Closed)
 * - Filter by severity (Critical, High, Medium, Low)
 * - Sort by: creation date, last updated, severity
 * - Click to view investigation detail
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Investigation, InvestigationStatus, EventSeverity } from '../types';
import { API_BASE_URL } from '../config';

interface InvestigationListProps {
  onSelectInvestigation: (investigation: Investigation) => void;
  onRefresh?: () => void;
}

type SortField = 'created_at' | 'updated_at' | 'severity' | 'status';
type SortDirection = 'asc' | 'desc';

export const InvestigationList: React.FC<InvestigationListProps> = ({
  onSelectInvestigation,
  onRefresh
}) => {
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<InvestigationStatus | 'all'>('all');
  const [selectedSeverity, setSelectedSeverity] = useState<EventSeverity | 'all'>('all');

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalCount, setTotalCount] = useState(0);

  // Sort state
  const [sortField, setSortField] = useState<SortField>('created_at');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  // Fetch investigations
  const fetchInvestigations = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Build query params
      const params = new URLSearchParams();
      params.append('page', currentPage.toString());
      params.append('page_size', pageSize.toString());
      params.append('sort_by', sortField);
      params.append('sort_order', sortDirection);

      if (searchQuery.trim()) {
        params.append('search', searchQuery);
      }

      if (selectedStatus !== 'all') {
        params.append('status', selectedStatus);
      }

      if (selectedSeverity !== 'all') {
        params.append('severity', selectedSeverity);
      }

      const response = await fetch(
        `${API_BASE_URL}/api/investigations?${params.toString()}`
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: Failed to fetch investigations`);
      }

      const data = await response.json();
      setInvestigations(data.investigations);
      setTotalCount(data.total_count);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Failed to fetch investigations:', err);
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, sortField, sortDirection, searchQuery, selectedStatus, selectedSeverity]);

  // Fetch on mount and when filters change
  useEffect(() => {
    fetchInvestigations();
  }, [fetchInvestigations]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, selectedStatus, selectedSeverity]);

  // Handle sort toggle
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      // Toggle direction
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  const getSeverityColor = (severity: EventSeverity): string => {
    const colors: Record<EventSeverity, string> = {
      CRITICAL: 'bg-red-100 text-red-800',
      HIGH: 'bg-orange-100 text-orange-800',
      MEDIUM: 'bg-yellow-100 text-yellow-800',
      LOW: 'bg-green-100 text-green-800',
      INFO: 'bg-blue-100 text-blue-800',
    };
    return colors[severity] || colors.INFO;
  };

  const getStatusColor = (status: InvestigationStatus): string => {
    const colors: Record<InvestigationStatus, string> = {
      OPEN: 'bg-red-100 text-red-800',
      IN_PROGRESS: 'bg-blue-100 text-blue-800',
      RESOLVED: 'bg-green-100 text-green-800',
      CLOSED: 'bg-gray-100 text-gray-800',
    };
    return colors[status] || colors.OPEN;
  };

  return (
    <div className="investigation-list p-6 space-y-4">
      {/* Filter Controls */}
      <div className="bg-white rounded-lg shadow p-4 space-y-4">
        <h2 className="text-xl font-bold text-gray-800">Investigations</h2>

        {/* Search Bar */}
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Search by ID, service, or title..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={() => fetchInvestigations()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            🔄 Refresh
          </button>
        </div>

        {/* Filter Row */}
        <div className="flex gap-4 flex-wrap">
          {/* Status Filter */}
          <div className="flex flex-col">
            <label className="text-sm font-semibold text-gray-700 mb-1">Status</label>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value as InvestigationStatus | 'all')}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Statuses</option>
              <option value="OPEN">Open</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="RESOLVED">Resolved</option>
              <option value="CLOSED">Closed</option>
            </select>
          </div>

          {/* Severity Filter */}
          <div className="flex flex-col">
            <label className="text-sm font-semibold text-gray-700 mb-1">Severity</label>
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value as EventSeverity | 'all')}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
              <option value="INFO">Info</option>
            </select>
          </div>

          {/* Page Size */}
          <div className="flex flex-col">
            <label className="text-sm font-semibold text-gray-700 mb-1">Per Page</label>
            <select
              value={pageSize}
              onChange={(e) => setPageSize(parseInt(e.target.value))}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </div>
        </div>

        {/* Results count */}
        <div className="text-sm text-gray-600">
          Showing {investigations.length} of {totalCount} investigations
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="text-center py-8">
          <div className="inline-block animate-spin">⏳</div>
          <p className="mt-2 text-gray-600">Loading investigations...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          <p className="font-semibold">Error loading investigations</p>
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* Investigations Table */}
      {!loading && investigations.length > 0 && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-100 border-b">
              <tr>
                <th
                  className="px-6 py-3 text-left text-sm font-semibold text-gray-700 cursor-pointer hover:bg-gray-200"
                  onClick={() => handleSort('created_at')}
                >
                  ID {sortField === 'created_at' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Service</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Title</th>
                <th
                  className="px-6 py-3 text-left text-sm font-semibold text-gray-700 cursor-pointer hover:bg-gray-200"
                  onClick={() => handleSort('severity')}
                >
                  Severity {sortField === 'severity' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th
                  className="px-6 py-3 text-left text-sm font-semibold text-gray-700 cursor-pointer hover:bg-gray-200"
                  onClick={() => handleSort('status')}
                >
                  Status {sortField === 'status' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Updated</th>
              </tr>
            </thead>
            <tbody>
              {investigations.map((investigation) => (
                <tr
                  key={investigation.id}
                  onClick={() => onSelectInvestigation(investigation)}
                  className="border-b hover:bg-blue-50 cursor-pointer transition"
                >
                  <td className="px-6 py-4 text-sm font-mono text-blue-600">{investigation.id}</td>
                  <td className="px-6 py-4 text-sm text-gray-800">{investigation.service}</td>
                  <td className="px-6 py-4 text-sm text-gray-800 truncate max-w-xs">{investigation.title}</td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getSeverityColor(investigation.severity)}`}>
                      {investigation.severity}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getStatusColor(investigation.status)}`}>
                      {investigation.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {new Date(investigation.updated_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Empty State */}
      {!loading && investigations.length === 0 && (
        <div className="bg-gray-50 rounded-lg p-8 text-center">
          <p className="text-gray-600 text-lg">No investigations found</p>
          <p className="text-gray-500 text-sm mt-1">Try adjusting your filters or search query</p>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-between items-center bg-white rounded-lg shadow p-4">
          <button
            onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
            className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg disabled:opacity-50 hover:bg-gray-300 transition"
          >
            ← Previous
          </button>

          <div className="flex gap-2">
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const pageNum = Math.max(1, currentPage - 2) + i;
              if (pageNum > totalPages) return null;
              return (
                <button
                  key={pageNum}
                  onClick={() => setCurrentPage(pageNum)}
                  className={`px-3 py-2 rounded-lg transition ${
                    pageNum === currentPage
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-800 hover:bg-gray-300'
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}
          </div>

          <button
            onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage === totalPages}
            className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg disabled:opacity-50 hover:bg-gray-300 transition"
          >
            Next →
          </button>

          <div className="text-sm text-gray-600">
            Page {currentPage} of {totalPages}
          </div>
        </div>
      )}
    </div>
  );
};

export default InvestigationList;
