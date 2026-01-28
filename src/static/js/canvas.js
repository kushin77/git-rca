/**
 * Investigation Canvas - Interactive Node-Link Editor
 *
 * Provides drag-and-drop canvas functionality for visualizing and editing
 * investigation relationships between events and annotations.
 */

class InvestigationCanvas {
    constructor(canvasId, investigationData) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.investigationData = investigationData;

        // Canvas state
        this.nodes = [];
        this.connections = [];
        this.selectedNode = null;
        this.selectedConnection = null;
        this.dragging = false;
        this.dragOffset = { x: 0, y: 0 };
        this.connectionMode = false;
        this.connectionStart = null;

        // Event handlers
        this.bindEvents();

        // Initialize with investigation data
        this.loadInvestigationData();

        // Initial render
        this.render();
    }

    bindEvents() {
        // Mouse events
        this.canvas.addEventListener('mousedown', this.handleMouseDown.bind(this));
        this.canvas.addEventListener('mousemove', this.handleMouseMove.bind(this));
        this.canvas.addEventListener('mouseup', this.handleMouseUp.bind(this));
        this.canvas.addEventListener('dblclick', this.handleDoubleClick.bind(this));
        this.canvas.addEventListener('contextmenu', this.handleContextMenu.bind(this));

        // Toolbar events
        document.getElementById('add-node-btn').addEventListener('click', this.addEventNode.bind(this));
        document.getElementById('add-annotation-btn').addEventListener('click', this.addAnnotationNode.bind(this));
        document.getElementById('clear-canvas-btn').addEventListener('click', this.clearCanvas.bind(this));
        document.getElementById('save-canvas-btn').addEventListener('click', this.saveCanvas.bind(this));

        // Window resize
        window.addEventListener('resize', this.handleResize.bind(this));
    }

    loadInvestigationData() {
        // Load events as nodes
        if (this.investigationData.events) {
            this.investigationData.events.forEach((event, index) => {
                this.addNode({
                    type: 'event',
                    eventType: event.source,
                    title: event.type,
                    description: event.description,
                    timestamp: event.timestamp,
                    data: event
                }, 100 + (index % 3) * 200, 100 + Math.floor(index / 3) * 150);
            });
        }

        // Load annotations as nodes
        if (this.investigationData.annotations) {
            this.investigationData.annotations.forEach((annotation, index) => {
                this.addNode({
                    type: 'annotation',
                    title: 'Annotation',
                    description: annotation.content,
                    author: annotation.author,
                    timestamp: annotation.timestamp,
                    data: annotation
                }, 600 + (index % 2) * 200, 100 + index * 120);
            });
        }
    }

    addNode(nodeData, x = 100, y = 100) {
        const node = {
            id: Date.now() + Math.random(),
            x: x,
            y: y,
            width: 140,
            height: 80,
            ...nodeData
        };
        this.nodes.push(node);
        this.render();
        return node;
    }

    addEventNode() {
        const node = this.addNode({
            type: 'event',
            eventType: 'manual',
            title: 'New Event',
            description: 'Click to edit',
            timestamp: new Date().toISOString()
        });
        this.editNode(node);
    }

    addAnnotationNode() {
        const node = this.addNode({
            type: 'annotation',
            title: 'New Annotation',
            description: 'Click to edit',
            author: 'Current User',
            timestamp: new Date().toISOString()
        });
        this.editNode(node);
    }

    clearCanvas() {
        if (confirm('Are you sure you want to clear the entire canvas? This will remove all nodes and connections.')) {
            this.nodes = [];
            this.connections = [];
            this.selectedNode = null;
            this.selectedConnection = null;
            this.render();
        }
    }

    saveCanvas() {
        const canvasData = {
            nodes: this.nodes,
            connections: this.connections,
            investigationId: this.investigationData.id
        };

        // Save to localStorage for now (in production, this would be saved to server)
        localStorage.setItem(`canvas_${this.investigationData.id}`, JSON.stringify(canvasData));

        alert('Canvas layout saved successfully!');
    }

    handleMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Check if clicking on a node
        for (let i = this.nodes.length - 1; i >= 0; i--) {
            const node = this.nodes[i];
            if (x >= node.x && x <= node.x + node.width &&
                y >= node.y && y <= node.y + node.height) {

                if (this.connectionMode && this.connectionStart && this.connectionStart !== node) {
                    // Create connection
                    this.addConnection(this.connectionStart, node);
                    this.connectionStart = null;
                    this.connectionMode = false;
                    this.selectedNode = null;
                } else {
                    // Start dragging
                    this.selectedNode = node;
                    this.dragging = true;
                    this.dragOffset = { x: x - node.x, y: y - node.y };
                    this.connectionMode = e.ctrlKey || e.metaKey; // Ctrl/Cmd for connection mode
                    if (this.connectionMode) {
                        this.connectionStart = node;
                    }
                }
                this.render();
                return;
            }
        }

        // Check if clicking on a connection
        for (let connection of this.connections) {
            if (this.isPointOnConnection(x, y, connection)) {
                this.selectedConnection = connection;
                this.render();
                return;
            }
        }

        // Click on empty space
        this.selectedNode = null;
        this.selectedConnection = null;
        this.connectionMode = false;
        this.connectionStart = null;
        this.render();
    }

    handleMouseMove(e) {
        if (!this.dragging || !this.selectedNode) return;

        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        this.selectedNode.x = x - this.dragOffset.x;
        this.selectedNode.y = y - this.dragOffset.y;

        this.render();
    }

    handleMouseUp() {
        this.dragging = false;
    }

    handleDoubleClick(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Find clicked node
        for (let node of this.nodes) {
            if (x >= node.x && x <= node.x + node.width &&
                y >= node.y && y <= node.y + node.height) {
                this.editNode(node);
                return;
            }
        }
    }

    handleContextMenu(e) {
        e.preventDefault();
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Find clicked node
        for (let i = this.nodes.length - 1; i >= 0; i--) {
            const node = this.nodes[i];
            if (x >= node.x && x <= node.x + node.width &&
                y >= node.y && y <= node.y + node.height) {
                if (confirm('Delete this node?')) {
                    this.deleteNode(node);
                }
                return;
            }
        }
    }

    handleResize() {
        // Adjust canvas size if needed
        const container = this.canvas.parentElement;
        if (container) {
            this.canvas.width = container.clientWidth - 40;
            this.canvas.height = Math.max(600, container.clientHeight - 100);
            this.render();
        }
    }

    addConnection(fromNode, toNode) {
        // Check if connection already exists
        const existing = this.connections.find(conn =>
            (conn.from === fromNode.id && conn.to === toNode.id) ||
            (conn.from === toNode.id && conn.to === fromNode.id)
        );

        if (!existing) {
            this.connections.push({
                id: Date.now() + Math.random(),
                from: fromNode.id,
                to: toNode.id,
                type: 'relationship'
            });
        }
    }

    deleteNode(node) {
        // Remove node
        this.nodes = this.nodes.filter(n => n.id !== node.id);

        // Remove connections to/from this node
        this.connections = this.connections.filter(conn =>
            conn.from !== node.id && conn.to !== node.id
        );

        if (this.selectedNode === node) {
            this.selectedNode = null;
        }

        this.render();
    }

    isPointOnConnection(x, y, connection) {
        const fromNode = this.nodes.find(n => n.id === connection.from);
        const toNode = this.nodes.find(n => n.id === connection.to);

        if (!fromNode || !toNode) return false;

        const fromX = fromNode.x + fromNode.width / 2;
        const fromY = fromNode.y + fromNode.height / 2;
        const toX = toNode.x + toNode.width / 2;
        const toY = toNode.y + toNode.height / 2;

        // Simple line distance check (could be improved with proper line distance calculation)
        const dist = this.pointToLineDistance(x, y, fromX, fromY, toX, toY);
        return dist < 5;
    }

    pointToLineDistance(x, y, x1, y1, x2, y2) {
        const A = x - x1;
        const B = y - y1;
        const C = x2 - x1;
        const D = y2 - y1;

        const dot = A * C + B * D;
        const lenSq = C * C + D * D;
        let param = -1;
        if (lenSq !== 0) {
            param = dot / lenSq;
        }

        let xx, yy;
        if (param < 0) {
            xx = x1;
            yy = y1;
        } else if (param > 1) {
            xx = x2;
            yy = y2;
        } else {
            xx = x1 + param * C;
            yy = y1 + param * D;
        }

        const dx = x - xx;
        const dy = y - yy;
        return Math.sqrt(dx * dx + dy * dy);
    }

    editNode(node) {
        // Create modal for editing
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <h3>Edit ${node.type === 'event' ? 'Event' : 'Annotation'}</h3>
                <label>Title:</label>
                <input type="text" id="edit-title" value="${node.title || ''}">

                <label>Description:</label>
                <textarea id="edit-description">${node.description || ''}</textarea>

                ${node.type === 'event' ? `
                    <label>Event Type:</label>
                    <select id="edit-event-type">
                        <option value="git" ${node.eventType === 'git' ? 'selected' : ''}>Git</option>
                        <option value="ci" ${node.eventType === 'ci' ? 'selected' : ''}>CI/CD</option>
                        <option value="logs" ${node.eventType === 'logs' ? 'selected' : ''}>Logs</option>
                        <option value="metrics" ${node.eventType === 'metrics' ? 'selected' : ''}>Metrics</option>
                        <option value="manual" ${node.eventType === 'manual' ? 'selected' : ''}>Manual</option>
                    </select>
                ` : `
                    <label>Author:</label>
                    <input type="text" id="edit-author" value="${node.author || ''}">
                `}

                <div class="modal-buttons">
                    <button id="save-btn" class="btn btn-success">Save</button>
                    <button id="cancel-btn" class="btn btn-secondary">Cancel</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Event handlers
        document.getElementById('save-btn').addEventListener('click', () => {
            node.title = document.getElementById('edit-title').value;
            node.description = document.getElementById('edit-description').value;

            if (node.type === 'event') {
                node.eventType = document.getElementById('edit-event-type').value;
            } else {
                node.author = document.getElementById('edit-author').value;
            }

            document.body.removeChild(modal);
            this.render();
        });

        document.getElementById('cancel-btn').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
    }

    render() {
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw connections first (behind nodes)
        this.connections.forEach(connection => {
            const fromNode = this.nodes.find(n => n.id === connection.from);
            const toNode = this.nodes.find(n => n.id === connection.to);

            if (fromNode && toNode) {
                this.ctx.beginPath();
                this.ctx.moveTo(fromNode.x + fromNode.width / 2, fromNode.y + fromNode.height / 2);
                this.ctx.lineTo(toNode.x + toNode.width / 2, toNode.y + toNode.height / 2);
                this.ctx.strokeStyle = connection === this.selectedConnection ? '#0066cc' : '#999';
                this.ctx.lineWidth = connection === this.selectedConnection ? 3 : 2;
                this.ctx.stroke();

                // Arrow head
                this.drawArrow(fromNode, toNode);
            }
        });

        // Draw nodes
        this.nodes.forEach(node => {
            this.drawNode(node);
        });

        // Draw connection preview if in connection mode
        if (this.connectionMode && this.connectionStart && this.selectedNode) {
            this.ctx.beginPath();
            this.ctx.moveTo(
                this.connectionStart.x + this.connectionStart.width / 2,
                this.connectionStart.y + this.connectionStart.height / 2
            );
            this.ctx.lineTo(
                this.selectedNode.x + this.selectedNode.width / 2,
                this.selectedNode.y + this.selectedNode.height / 2
            );
            this.ctx.strokeStyle = '#0066cc';
            this.ctx.lineWidth = 2;
            this.ctx.setLineDash([5, 5]);
            this.ctx.stroke();
            this.ctx.setLineDash([]);
        }
    }

    drawNode(node) {
        // Node background
        this.ctx.fillStyle = node === this.selectedNode ? '#e7f3ff' : 'white';
        this.ctx.fillRect(node.x, node.y, node.width, node.height);

        // Node border
        this.ctx.strokeStyle = node === this.selectedNode ? '#0066cc' : '#ddd';
        this.ctx.lineWidth = node === this.selectedNode ? 3 : 2;
        this.ctx.strokeRect(node.x, node.y, node.width, node.height);

        // Left border color based on type
        if (node.type === 'event') {
            this.ctx.fillStyle = this.getEventColor(node.eventType);
            this.ctx.fillRect(node.x, node.y, 4, node.height);
        } else if (node.type === 'annotation') {
            this.ctx.fillStyle = '#6c757d';
            this.ctx.fillRect(node.x, node.y, 4, node.height);
        }

        // Node content
        this.ctx.fillStyle = '#333';
        this.ctx.font = 'bold 12px Arial';
        this.ctx.fillText(node.title || 'Untitled', node.x + 8, node.y + 20);

        this.ctx.font = '11px Arial';
        this.ctx.fillStyle = '#666';

        // Wrap description text
        const words = (node.description || '').split(' ');
        let line = '';
        let y = node.y + 35;
        for (let word of words) {
            const testLine = line + word + ' ';
            const metrics = this.ctx.measureText(testLine);
            if (metrics.width > node.width - 16 && line !== '') {
                this.ctx.fillText(line, node.x + 8, y);
                line = word + ' ';
                y += 12;
            } else {
                line = testLine;
            }
        }
        this.ctx.fillText(line, node.x + 8, y);
    }

    drawArrow(fromNode, toNode) {
        const fromX = fromNode.x + fromNode.width / 2;
        const fromY = fromNode.y + fromNode.height / 2;
        const toX = toNode.x + toNode.width / 2;
        const toY = toNode.y + toNode.height / 2;

        const angle = Math.atan2(toY - fromY, toX - fromX);
        const arrowLength = 10;

        this.ctx.beginPath();
        this.ctx.moveTo(toX, toY);
        this.ctx.lineTo(
            toX - arrowLength * Math.cos(angle - Math.PI / 6),
            toY - arrowLength * Math.sin(angle - Math.PI / 6)
        );
        this.ctx.moveTo(toX, toY);
        this.ctx.lineTo(
            toX - arrowLength * Math.cos(angle + Math.PI / 6),
            toY - arrowLength * Math.sin(angle + Math.PI / 6)
        );
        this.ctx.strokeStyle = '#999';
        this.ctx.lineWidth = 2;
        this.ctx.stroke();
    }

    getEventColor(eventType) {
        const colors = {
            'git': '#f05033',
            'ci': '#00add8',
            'logs': '#ffd43b',
            'metrics': '#20c997',
            'manual': '#6c757d'
        };
        return colors[eventType] || '#6c757d';
    }
}

// Initialize canvas when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Get investigation data from template
    const investigationData = window.INVESTIGATION_DATA || {};

    if (document.getElementById('investigation-canvas')) {
        window.investigationCanvas = new InvestigationCanvas('investigation-canvas', investigationData);
    }
});