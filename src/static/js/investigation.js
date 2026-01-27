/**
 * Investigation Canvas Interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize annotation handlers
    initializeAnnotationHandlers();
    // Initialize keyboard shortcuts
    initializeKeyboardShortcuts();
    // Load investigation data if available
    loadInvestigationData();
});

/**
 * Initialize annotation action handlers
 */
function initializeAnnotationHandlers() {
    const actionLinks = document.querySelectorAll('.annotation-action-link');
    actionLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const action = this.getAttribute('data-action');
            const annotationId = this.getAttribute('data-id');
            
            if (action === 'reply') {
                toggleReplyForm(e, annotationId);
            } else if (action === 'edit') {
                editAnnotation(e, annotationId);
            }
        });
    });
}

/**
 * Toggle reply form visibility
 */
function toggleReplyForm(event, annotationId) {
    if (event) {
        event.preventDefault();
    }
    
    const replyForm = document.getElementById(`reply-form-${annotationId}`);
    if (replyForm) {
        replyForm.style.display = replyForm.style.display === 'none' ? 'block' : 'none';
        
        // Focus the textarea if showing
        if (replyForm.style.display === 'block') {
            const textarea = replyForm.querySelector('.reply-textarea');
            if (textarea) {
                textarea.focus();
            }
        }
    }
}

/**
 * Submit a reply to an annotation
 */
function submitReply(parentAnnotationId) {
    const replyForm = document.getElementById(`reply-form-${parentAnnotationId}`);
    if (!replyForm) return;
    
    const textarea = replyForm.querySelector('.reply-textarea');
    const replyText = textarea.value.trim();
    
    if (!replyText) {
        alert('Please enter a reply.');
        return;
    }
    
    const investigationId = window.location.pathname.split('/').pop();
    
    // Submit the reply as an annotation with parent_annotation_id
    fetch(`/api/investigations/${investigationId}/annotations`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            author: 'Current User',  // Will be replaced with actual user
            text: replyText,
            parent_annotation_id: parentAnnotationId,
        }),
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to post reply');
        
        // Clear textarea and close form
        textarea.value = '';
        toggleReplyForm(null, parentAnnotationId);
        
        // Reload annotations
        location.reload();
    })
    .catch(error => {
        console.error('Error posting reply:', error);
        alert('Failed to post reply. Please try again.');
    });
}

/**
 * Edit an annotation
 */
function editAnnotation(event, annotationId) {
    if (event) {
        event.preventDefault();
    }
    
    console.log('Edit annotation:', annotationId);
    // Implementation: Show edit form or inline editor
    alert('Edit functionality coming soon.');
}

/**
 * Initialize keyboard shortcuts
 */
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl+S / Cmd+S: Save
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            saveInvestigation();
        }
        
        // Ctrl+P / Cmd+P: Print
        if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
            e.preventDefault();
            printCanvas();
        }
    });
}

/**
 * Load investigation data from API
 */
function loadInvestigationData() {
    const investigationId = window.location.pathname.match(/\/investigations\/([^\/]+)/);
    if (!investigationId) return;
    
    // Data would be loaded from API in production
    console.log('Loaded investigation:', investigationId[1]);
}

/**
 * Scroll to section smoothly
 */
function scrollToSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

/**
 * Export investigation as JSON
 */
function exportAsJSON() {
    const investigation = {
        title: document.getElementById('title').value,
        description: document.getElementById('description').value,
        root_cause: document.getElementById('root-cause').value,
        fix: document.getElementById('fix').value,
        prevention: document.getElementById('prevention').value,
        status: document.getElementById('status').value,
        impact: document.getElementById('impact').value,
        area: document.getElementById('area').value,
        component: document.getElementById('component').value,
        exported_at: new Date().toISOString()
    };
    
    const dataStr = JSON.stringify(investigation, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `investigation-${investigation.title.replace(/\s+/g, '-').toLowerCase()}.json`;
    link.click();
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

/**
 * Validate form before saving
 */
function validateInvestigation() {
    const title = document.getElementById('title').value.trim();
    const rootCause = document.getElementById('root-cause').value.trim();
    
    if (!title) {
        alert('Please enter an investigation title');
        return false;
    }
    
    if (!rootCause && document.getElementById('status').value === 'resolved') {
        alert('Please document the root cause before marking as resolved');
        return false;
    }
    
    return true;
}

/**
 * Auto-save functionality
 */
let autoSaveTimer;
function enableAutoSave(interval = 30000) {
    const inputs = document.querySelectorAll('input[type="text"], textarea, select');
    inputs.forEach(input => {
        input.addEventListener('change', function() {
            clearTimeout(autoSaveTimer);
            autoSaveTimer = setTimeout(() => {
                console.log('Auto-saving investigation...');
                saveInvestigation();
            }, interval);
        });
    });
}

/**
 * Timeline event highlighting
 */
function highlightTimelineEvent(eventIndex) {
    const events = document.querySelectorAll('.timeline-event');
    events.forEach((event, index) => {
        if (index === eventIndex) {
            event.style.backgroundColor = '#fff3cd';
            event.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
            event.style.backgroundColor = '';
        }
    });
}

/**
 * Annotation count update
 */
function updateAnnotationCount(count) {
    const countBadge = document.querySelector('.annotations-count');
    if (countBadge) {
        countBadge.textContent = count;
    }
}

// Export functions for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        saveInvestigation,
        addAnnotation,
        markResolved,
        printCanvas,
        exportAsJSON,
        validateInvestigation
    };
}
