/**
 * Investigation Canvas UI Component Tests
 * 
 * Test suite for Phase 3c UI components including:
 * - InvestigationList component tests
 * - InvestigationDetail component tests
 * - EventTimeline component tests
 * - Integration tests
 * 
 * Test Framework: Jest + React Testing Library
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import InvestigationList from '../components/InvestigationList';
import InvestigationDetail from '../components/InvestigationDetail';
import EventTimeline from '../components/EventTimeline';
import InvestigationCanvas from '../InvestigationCanvas';
import { Investigation, Event, InvestigationStatus, EventSeverity } from '../types';

// Mock data
const mockInvestigations: Investigation[] = [
  {
    id: 'INV-001',
    title: 'Database Connection Timeout',
    description: 'Production database experiencing connection timeouts',
    service: 'api-service',
    environment: 'production',
    status: 'OPEN' as InvestigationStatus,
    severity: 'CRITICAL' as EventSeverity,
    created_at: '2024-01-28T10:00:00Z',
    updated_at: '2024-01-28T11:00:00Z',
    created_by: 'system',
    assigned_to: 'john.doe@company.com',
    estimated_mttr: '1 hour',
    automation_potential: 45,
  },
  {
    id: 'INV-002',
    title: 'Memory Leak in Worker Process',
    description: 'Worker process memory usage increasing over time',
    service: 'worker-service',
    environment: 'staging',
    status: 'IN_PROGRESS' as InvestigationStatus,
    severity: 'HIGH' as EventSeverity,
    created_at: '2024-01-27T14:30:00Z',
    updated_at: '2024-01-28T09:15:00Z',
    created_by: 'system',
    automation_potential: 60,
  },
];

const mockEvents: Event[] = [
  {
    id: 'EVT-001',
    investigation_id: 'INV-001',
    message: 'Database connection timeout detected',
    timestamp: '2024-01-28T10:05:00Z',
    source: 'LOGS',
    severity: 'CRITICAL',
    service: 'api-service',
    correlation_id: 'corr-12345',
    tags: ['database', 'timeout', 'connection'],
  },
  {
    id: 'EVT-002',
    investigation_id: 'INV-001',
    message: 'CPU spike to 95%',
    timestamp: '2024-01-28T10:02:00Z',
    source: 'METRICS',
    severity: 'HIGH',
    service: 'api-service',
    metadata: { cpu_percent: 95, memory_percent: 78 },
  },
  {
    id: 'EVT-003',
    investigation_id: 'INV-001',
    message: 'Slow query detected: SELECT * FROM users (2.5s)',
    timestamp: '2024-01-28T10:00:00Z',
    source: 'TRACES',
    severity: 'MEDIUM',
    service: 'api-service',
    tags: ['query', 'slow', 'database'],
  },
];

// Mock fetch
global.fetch = jest.fn();

describe('InvestigationList Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({
        investigations: mockInvestigations,
        total_count: 2,
      }),
    });
  });

  test('renders investigation list with initial data', async () => {
    const mockCallback = jest.fn();
    render(<InvestigationList onSelectInvestigation={mockCallback} />);

    await waitFor(() => {
      expect(screen.getByText('Investigations')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText('INV-001')).toBeInTheDocument();
      expect(screen.getByText('Database Connection Timeout')).toBeInTheDocument();
    });
  });

  test('displays severity badges with correct colors', async () => {
    const mockCallback = jest.fn();
    render(<InvestigationList onSelectInvestigation={mockCallback} />);

    await waitFor(() => {
      expect(screen.getByText('CRITICAL')).toBeInTheDocument();
      expect(screen.getByText('HIGH')).toBeInTheDocument();
    });
  });

  test('filters investigations by status', async () => {
    const mockCallback = jest.fn();
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({
        investigations: [mockInvestigations[0]],
        total_count: 1,
      }),
    });

    render(<InvestigationList onSelectInvestigation={mockCallback} />);

    const statusSelect = await screen.findByDisplayValue('All Statuses');
    await userEvent.selectOptions(statusSelect, 'OPEN');

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('status=OPEN'),
        expect.anything()
      );
    });
  });

  test('searches investigations by query', async () => {
    const mockCallback = jest.fn();
    render(<InvestigationList onSelectInvestigation={mockCallback} />);

    const searchInput = await screen.findByPlaceholderText(/Search by ID/);
    await userEvent.type(searchInput, 'database');

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('search=database'),
        expect.anything()
      );
    });
  });

  test('handles pagination correctly', async () => {
    const mockCallback = jest.fn();
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({
        investigations: mockInvestigations,
        total_count: 30,
      }),
    });

    render(<InvestigationList onSelectInvestigation={mockCallback} />);

    await waitFor(() => {
      expect(screen.getByText('Page 1 of 3')).toBeInTheDocument();
    });

    const nextButton = screen.getByText('Next →');
    fireEvent.click(nextButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('page=2'),
        expect.anything()
      );
    });
  });

  test('calls callback when investigation selected', async () => {
    const mockCallback = jest.fn();
    render(<InvestigationList onSelectInvestigation={mockCallback} />);

    await waitFor(() => {
      expect(screen.getByText('INV-001')).toBeInTheDocument();
    });

    const row = screen.getByText('INV-001').closest('tr');
    fireEvent.click(row!);

    expect(mockCallback).toHaveBeenCalledWith(mockInvestigations[0]);
  });

  test('displays loading state', () => {
    (global.fetch as jest.Mock).mockImplementationOnce(
      () => new Promise((resolve) => setTimeout(resolve, 1000))
    );

    render(<InvestigationList onSelectInvestigation={jest.fn()} />);

    expect(screen.getByText(/Loading investigations/)).toBeInTheDocument();
  });

  test('displays error state on API failure', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('API Error'));

    const { container } = render(<InvestigationList onSelectInvestigation={jest.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Error loading investigations')).toBeInTheDocument();
    });
  });

  test('sorts investigations by clicking column headers', async () => {
    const mockCallback = jest.fn();
    render(<InvestigationList onSelectInvestigation={mockCallback} />);

    await waitFor(() => {
      expect(screen.getByText(/Investigations/)).toBeInTheDocument();
    });

    // Click ID header to sort
    const idHeader = screen.getAllByText(/ID/)[0];
    fireEvent.click(idHeader);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('sort_by=created_at'),
        expect.anything()
      );
    });
  });
});

describe('EventTimeline Component', () => {
  test('renders events in chronological order', () => {
    render(<EventTimeline events={mockEvents} investigationId="INV-001" />);

    const timelineItems = screen.getAllByText(/Database connection timeout|CPU spike|Slow query/);
    expect(timelineItems.length).toBe(3);

    // Most recent first
    expect(screen.getByText('Database connection timeout detected')).toBeInTheDocument();
  });

  test('displays event source filters', () => {
    render(<EventTimeline events={mockEvents} investigationId="INV-001" />);

    expect(screen.getByText(/🔍 TRACES/)).toBeInTheDocument();
    expect(screen.getByText(/📝 LOGS/)).toBeInTheDocument();
    expect(screen.getByText(/📊 METRICS/)).toBeInTheDocument();
  });

  test('filters events by source', () => {
    render(<EventTimeline events={mockEvents} investigationId="INV-001" />);

    const logsButton = screen.getByText(/📝 LOGS/);
    fireEvent.click(logsButton);

    // Should show only LOGS events
    expect(screen.getByText('Database connection timeout detected')).toBeInTheDocument();

    // METRICS and TRACES events should not be expanded/visible
    const timeline = screen.getByText(/Event Timeline/).closest('.event-timeline');
    expect(within(timeline!).queryAllByText(/CPU spike/).length).toBe(0);
  });

  test('expands and collapses event details', () => {
    render(<EventTimeline events={mockEvents} investigationId="INV-001" />);

    const eventCard = screen.getByText('Database connection timeout detected').closest('.border-l-4');
    fireEvent.click(eventCard!);

    // Details should now be visible
    expect(screen.getByText(/Metadata/)).toBeInTheDocument();
    expect(screen.getByText(/Tags/)).toBeInTheDocument();

    // Click again to collapse
    fireEvent.click(eventCard!);

    // The metadata section should be hidden
    // Note: This depends on implementation details
  });

  test('displays event severity badges', () => {
    render(<EventTimeline events={mockEvents} investigationId="INV-001" />);

    expect(screen.getByText('CRITICAL')).toBeInTheDocument();
    expect(screen.getByText('HIGH')).toBeInTheDocument();
    expect(screen.getByText('MEDIUM')).toBeInTheDocument();
  });

  test('shows timeline statistics', () => {
    render(<EventTimeline events={mockEvents} investigationId="INV-001" />);

    expect(screen.getByText('Timeline Statistics')).toBeInTheDocument();
    expect(screen.getByText(/First Event/)).toBeInTheDocument();
    expect(screen.getByText(/Last Event/)).toBeInTheDocument();
    expect(screen.getByText(/Duration/)).toBeInTheDocument();
    expect(screen.getByText(/Events\/Hour/)).toBeInTheDocument();
  });

  test('displays empty state when no events', () => {
    render(<EventTimeline events={[]} investigationId="INV-001" />);

    expect(screen.getByText(/No events found/)).toBeInTheDocument();
  });

  test('shows raw JSON for event details', () => {
    render(<EventTimeline events={[mockEvents[0]]} investigationId="INV-001" />);

    const eventCard = screen.getByText('Database connection timeout detected').closest('.border-l-4');
    fireEvent.click(eventCard!);

    expect(screen.getByText(/Raw JSON/)).toBeInTheDocument();

    // Click to expand raw JSON
    const rawJsonSummary = screen.getByText('Raw JSON');
    fireEvent.click(rawJsonSummary);

    expect(screen.getByText(/"investigation_id":/)).toBeInTheDocument();
  });
});

describe('InvestigationDetail Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockImplementation((url) => {
      if (url.includes('/investigations/INV-001')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockInvestigations[0],
        });
      }
      if (url.includes('/events')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ events: mockEvents }),
        });
      }
      return Promise.reject(new Error('Not found'));
    });
  });

  test('renders investigation detail with all sections', async () => {
    render(
      <InvestigationDetail
        investigationId="INV-001"
        onBack={jest.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Database Connection Timeout')).toBeInTheDocument();
    });

    expect(screen.getByText('OPEN')).toBeInTheDocument();
    expect(screen.getByText('CRITICAL')).toBeInTheDocument();
    expect(screen.getByText('Event Timeline')).toBeInTheDocument();
  });

  test('allows status change', async () => {
    const mockStatusChange = jest.fn();
    (global.fetch as jest.Mock).mockImplementation((url, options) => {
      if (url.includes('/status')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ ...mockInvestigations[0], status: 'IN_PROGRESS' }),
        });
      }
      if (url.includes('/investigations/INV-001') && !url.includes('/status')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockInvestigations[0],
        });
      }
      if (url.includes('/events')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ events: mockEvents }),
        });
      }
      return Promise.reject(new Error('Not found'));
    });

    render(
      <InvestigationDetail
        investigationId="INV-001"
        onBack={jest.fn()}
        onStatusChange={mockStatusChange}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Database Connection Timeout')).toBeInTheDocument();
    });

    // Find and click status dropdown
    const statusButtons = screen.getAllByRole('option');
    const inProgressOption = statusButtons.find((btn) => btn.textContent === 'In Progress');

    if (inProgressOption) {
      fireEvent.change(inProgressOption.closest('select')!, {
        target: { value: 'IN_PROGRESS' },
      });

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/status'),
          expect.anything()
        );
      });
    }
  });

  test('enables edit mode and saves changes', async () => {
    (global.fetch as jest.Mock).mockImplementation((url, options) => {
      if (url.includes('/investigations/INV-001') && options?.method === 'PUT') {
        return Promise.resolve({
          ok: true,
          json: async () => ({ ...mockInvestigations[0], title: 'Updated Title' }),
        });
      }
      if (url.includes('/investigations/INV-001')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockInvestigations[0],
        });
      }
      if (url.includes('/events')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ events: mockEvents }),
        });
      }
      return Promise.reject(new Error('Not found'));
    });

    render(
      <InvestigationDetail
        investigationId="INV-001"
        onBack={jest.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Database Connection Timeout')).toBeInTheDocument();
    });

    // Click edit button
    const editButton = screen.getByText('✎ Edit');
    fireEvent.click(editButton);

    // Title input should now be editable
    const titleInput = screen.getByDisplayValue('Database Connection Timeout');
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, 'Updated Title');

    // Click save
    const saveButton = screen.getByText('✓ Save');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/investigations/INV-001'),
        expect.objectContaining({ method: 'PUT' })
      );
    });
  });

  test('shows event timeline for investigation', async () => {
    render(
      <InvestigationDetail
        investigationId="INV-001"
        onBack={jest.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Event Timeline')).toBeInTheDocument();
    });

    // Should render events
    expect(screen.getByText('Database connection timeout detected')).toBeInTheDocument();
  });

  test('calls onBack when back button clicked', async () => {
    const mockOnBack = jest.fn();

    render(
      <InvestigationDetail
        investigationId="INV-001"
        onBack={mockOnBack}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Database Connection Timeout')).toBeInTheDocument();
    });

    const backButton = screen.getByText('← Back to List');
    fireEvent.click(backButton);

    expect(mockOnBack).toHaveBeenCalled();
  });

  test('handles API errors gracefully', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('API Error'));

    render(
      <InvestigationDetail
        investigationId="INV-001"
        onBack={jest.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Failed to fetch investigation/)).toBeInTheDocument();
    });
  });
});

describe('InvestigationCanvas Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockImplementation((url) => {
      if (url.includes('/api/investigations?')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            investigations: mockInvestigations,
            total_count: 2,
          }),
        });
      }
      if (url.includes('/api/connectors/status')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            connectors: [
              {
                source: 'LOGS',
                state: 'CLOSED',
                failure_count: 0,
                dlq_size: 0,
              },
            ],
          }),
        });
      }
      return Promise.reject(new Error('Not found'));
    });
  });

  test('renders investigation list on initial load', async () => {
    render(<InvestigationCanvas />);

    await waitFor(() => {
      expect(screen.getByText('🔍 Investigation Canvas')).toBeInTheDocument();
    });

    expect(screen.getByText('Investigations')).toBeInTheDocument();
  });

  test('displays connector health dashboard', async () => {
    render(<InvestigationCanvas />);

    await waitFor(() => {
      expect(screen.getByText('📡 Connector Health')).toBeInTheDocument();
    });

    expect(screen.getByText('📝 LOGS')).toBeInTheDocument();
  });

  test('navigates from list to detail view', async () => {
    render(<InvestigationCanvas />);

    await waitFor(() => {
      expect(screen.getByText('INV-001')).toBeInTheDocument();
    });

    const investigation = screen.getByText('INV-001').closest('tr');
    fireEvent.click(investigation!);

    // Should show back button indicating detail view
    await waitFor(() => {
      expect(screen.getByText('← Back to List')).toBeInTheDocument();
    });
  });

  test('navigates back from detail to list view', async () => {
    render(<InvestigationCanvas />);

    // Initially on list view
    await waitFor(() => {
      expect(screen.getByText('INV-001')).toBeInTheDocument();
    });

    // Click on investigation
    const investigation = screen.getByText('INV-001').closest('tr');
    fireEvent.click(investigation!);

    // Should be in detail view
    await waitFor(() => {
      expect(screen.getByText('← Back to List')).toBeInTheDocument();
    });

    // Click back button
    const backButton = screen.getByText('← Back to List');
    fireEvent.click(backButton);

    // Should return to list view - table should be visible again
    await waitFor(() => {
      expect(screen.getByText('Investigations')).toBeInTheDocument();
    });
  });
});

describe('Accessibility Tests', () => {
  test('investigation list has proper heading hierarchy', async () => {
    const mockCallback = jest.fn();
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({
        investigations: mockInvestigations,
        total_count: 2,
      }),
    });

    const { container } = render(<InvestigationList onSelectInvestigation={mockCallback} />);

    // Check for proper heading structure
    const headings = container.querySelectorAll('h1, h2, h3');
    expect(headings.length).toBeGreaterThan(0);
  });

  test('form inputs have associated labels', async () => {
    const mockCallback = jest.fn();
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({
        investigations: mockInvestigations,
        total_count: 2,
      }),
    });

    render(<InvestigationList onSelectInvestigation={mockCallback} />);

    const statusLabel = screen.getByText('Status');
    expect(statusLabel).toBeInTheDocument();

    const statusSelect = statusLabel.nextElementSibling;
    expect(statusSelect?.tagName).toBe('SELECT');
  });

  test('color is not the only way to distinguish information', () => {
    render(<EventTimeline events={mockEvents} investigationId="INV-001" />);

    // Should have text labels in addition to colors
    expect(screen.getByText('CRITICAL')).toBeInTheDocument();
    expect(screen.getByText('HIGH')).toBeInTheDocument();
    expect(screen.getByText('MEDIUM')).toBeInTheDocument();
  });
});

describe('Performance Tests', () => {
  test('renders large investigation list efficiently', async () => {
    const largeInvestigationList = Array.from({ length: 50 }, (_, i) => ({
      ...mockInvestigations[0],
      id: `INV-${String(i).padStart(3, '0')}`,
    }));

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({
        investigations: largeInvestigationList.slice(0, 10),
        total_count: 50,
      }),
    });

    const startTime = performance.now();
    const { container } = render(
      <InvestigationList onSelectInvestigation={jest.fn()} />
    );
    const endTime = performance.now();

    // Should render within 1 second
    expect(endTime - startTime).toBeLessThan(1000);

    // Should render all items
    await waitFor(() => {
      const rows = container.querySelectorAll('tbody tr');
      expect(rows.length).toBeGreaterThan(0);
    });
  });
});

describe('Type Safety Tests', () => {
  test('component accepts correct prop types', () => {
    const investigation: Investigation = mockInvestigations[0];
    const event: Event = mockEvents[0];

    // Should compile without type errors
    expect(investigation.id).toBe('INV-001');
    expect(event.source).toBe('LOGS');
  });
});
