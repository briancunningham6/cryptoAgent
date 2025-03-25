/**
 * Main application JavaScript file
 * Contains shared functionality used across multiple pages
 */

// Utility function to format dates
function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Utility function to format numbers with 2 decimal places
function formatNumber(number, decimals = 2) {
    if (number === null || number === undefined) return 'N/A';
    return parseFloat(number).toFixed(decimals);
}

// Utility function to create status badges
function createStatusBadge(status) {
    let badgeClass = 'bg-secondary';
    
    if (status === 'up' || status === 'success' || status === 'active' || status === 'open') {
        badgeClass = 'bg-success';
    } else if (status === 'down' || status === 'danger' || status === 'error' || status === 'failed') {
        badgeClass = 'bg-danger';
    } else if (status === 'warning' || status === 'caution' || status === 'pending') {
        badgeClass = 'bg-warning';
    } else if (status === 'info' || status === 'neutral' || status === 'closed') {
        badgeClass = 'bg-info';
    }
    
    return `<span class="badge ${badgeClass}">${status.toUpperCase()}</span>`;
}

// Function to show alerts
function showAlert(message, type = 'info', container = 'body', timeout = 5000) {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.setAttribute('role', 'alert');
    
    // Add message
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Add to container
    const containerEl = typeof container === 'string' ? document.querySelector(container) : container;
    if (containerEl) {
        containerEl.prepend(alertDiv);
    }
    
    // Auto-remove after timeout
    if (timeout > 0) {
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.classList.remove('show');
                setTimeout(() => {
                    if (alertDiv.parentNode) {
                        alertDiv.parentNode.removeChild(alertDiv);
                    }
                }, 150);
            }
        }, timeout);
    }
    
    return alertDiv;
}

// Function to make API requests with error handling
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, options);
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API request failed: ${response.status} ${response.statusText}\n${errorText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Request Error:', error);
        showAlert(`API Error: ${error.message}`, 'danger');
        throw error;
    }
}

// Check the status of the Trading API
function checkTradingApiStatus() {
    // Try to make a lightweight API call to check status
    fetch('/api/status/check-api', { 
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        },
        // Short timeout to prevent blocking the UI
        signal: AbortSignal.timeout(2000)
    })
    .then(response => response.json())
    .then(data => {
        const alertElement = document.getElementById('api-status-alert');
        if (alertElement) {
            if (data.api_available === false) {
                // Show the alert if API is not available
                alertElement.style.display = 'block';
            } else {
                // Hide the alert if API is available
                alertElement.style.display = 'none';
            }
        }
    })
    .catch(error => {
        // If there's an error with the status check, assume API is down
        console.error('API status check failed:', error);
        const alertElement = document.getElementById('api-status-alert');
        if (alertElement) {
            alertElement.style.display = 'block';
        }
    });
}

// Setup common tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(tooltip => {
        new bootstrap.Tooltip(tooltip);
    });
    
    // Initialize popovers
    const popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
    popovers.forEach(popover => {
        new bootstrap.Popover(popover);
    });
    
    // Setup navigation active state
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href === currentPath) {
            link.classList.add('active');
        }
    });
    
    // Check API status when page loads
    checkTradingApiStatus();
    
    // Periodically check API status
    setInterval(checkTradingApiStatus, 30000); // Check every 30 seconds
});

// Auto refresh functionality
function setupAutoRefresh(intervalSeconds = 30) {
    // Check if auto-refresh is enabled via URL parameter
    const urlParams = new URLSearchParams(window.location.search);
    const autoRefreshParam = urlParams.get('auto_refresh');
    
    if (autoRefreshParam === 'false') {
        return;
    }
    
    // Add auto-refresh indicator to page
    const refreshIndicator = document.createElement('div');
    refreshIndicator.className = 'auto-refresh-indicator';
    refreshIndicator.innerHTML = `
        <small class="text-muted">
            <i class="fas fa-sync-alt"></i> Auto-refreshing in <span id="refresh-countdown">${intervalSeconds}</span>s
            <a href="#" id="stop-auto-refresh">(Stop)</a>
        </small>
    `;
    
    // Add to page if there's a footer
    const footer = document.querySelector('footer');
    if (footer) {
        footer.prepend(refreshIndicator);
    }
    
    // Setup countdown timer
    let countdown = intervalSeconds;
    const countdownElement = document.getElementById('refresh-countdown');
    
    const timer = setInterval(() => {
        countdown -= 1;
        if (countdownElement) {
            countdownElement.textContent = countdown;
        }
        
        if (countdown <= 0) {
            window.location.reload();
        }
    }, 1000);
    
    // Setup stop button
    const stopButton = document.getElementById('stop-auto-refresh');
    if (stopButton) {
        stopButton.addEventListener('click', function(e) {
            e.preventDefault();
            clearInterval(timer);
            
            // Update URL to disable auto-refresh
            const newUrl = new URL(window.location);
            newUrl.searchParams.set('auto_refresh', 'false');
            window.history.replaceState({}, '', newUrl);
            
            // Update indicator
            refreshIndicator.innerHTML = `
                <small class="text-muted">
                    <i class="fas fa-pause"></i> Auto-refresh paused
                    <a href="javascript:window.location.reload();">(Refresh now)</a>
                </small>
            `;
        });
    }
}
