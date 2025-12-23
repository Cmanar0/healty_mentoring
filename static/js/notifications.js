/**
 * Unified Notification System
 * Usage: showNotification(message, type)
 * Types: 'note', 'warning', 'error', 'success'
 */

function showNotification(message, type = 'note') {
    // Ensure container exists
    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        // Force z-index via inline style to override any CSS specificity issues
        container.style.zIndex = '99999';
        container.style.position = 'fixed';
        // Append at the very end of body to ensure it's above all other elements
        // This ensures it's rendered after any overlays/modals
        document.body.appendChild(container);
    } else {
        // If container exists, move it to the end of body to ensure proper stacking
        // This handles cases where overlays are added after notifications
        if (container.parentNode !== document.body || container.nextSibling !== null) {
            document.body.appendChild(container);
        }
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `app-notification app-notification-${type}`;
    
    // Icon selection
    let iconClass = 'fa-info-circle';
    if (type === 'success') iconClass = 'fa-check-circle';
    if (type === 'error') iconClass = 'fa-exclamation-circle';
    if (type === 'warning') iconClass = 'fa-exclamation-triangle';
    
    notification.innerHTML = `
        <div class="notification-content-wrapper">
            <div class="notification-icon">
                <i class="fas ${iconClass}"></i>
            </div>
            <div class="notification-message">${message}</div>
            <button class="notification-close" onclick="this.closest('.app-notification').remove()">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="notification-progress"></div>
    `;
    
    // Add to container
    // Prepend to show newest at top, or append for bottom. 
    // Given the fixed position top-right, appending usually stacks them downwards which is standard.
    container.appendChild(notification);
    
    // CRITICAL: Always ensure container is the last child of body
    // This ensures it's above all overlays/modals, even those with backdrop-filter
    // backdrop-filter creates a stacking context, but DOM order + z-index ensures proper stacking
    // Move immediately and also in next frame to catch any late DOM changes
    if (container.parentNode === document.body) {
        document.body.appendChild(container);
    }
    requestAnimationFrame(() => {
        if (container.parentNode === document.body) {
            document.body.appendChild(container);
        }
    });
    
    // Show notification
    // Small delay to allow DOM insertion before adding active class for transition
    requestAnimationFrame(() => {
        notification.classList.add('active');
    });
    
    // Auto-dismiss logic
    const duration = 5000;
    const progress = notification.querySelector('.notification-progress');
    let startTime = Date.now();
    let remaining = duration;
    let timerId = null;
    let animationId = null;
    let isPaused = false;
    
    const dismiss = () => {
        notification.classList.remove('active');
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(50px) scale(0.95)';
        
        setTimeout(() => {
            if (notification.parentNode) notification.remove();
            
            // Remove container if empty to clean up
            if (container.childNodes.length === 0) {
                container.remove();
            }
        }, 500); // Wait for transition (0.5s in CSS)
    };
    
    const startTimer = () => {
        startTime = Date.now();
        timerId = setTimeout(dismiss, remaining);
        
        // Animate progress bar
        const animate = () => {
            if (isPaused) return;
            
            const elapsed = Date.now() - startTime;
            const currentRemaining = Math.max(0, remaining - elapsed);
            const percentage = (currentRemaining / duration) * 100;
            
            if (progress) {
                progress.style.width = `${percentage}%`;
            }
            
            if (currentRemaining > 0) {
                animationId = requestAnimationFrame(animate);
            }
        };
        animationId = requestAnimationFrame(animate);
    };
    
    const pauseTimer = () => {
        isPaused = true;
        clearTimeout(timerId);
        cancelAnimationFrame(animationId);
        remaining -= (Date.now() - startTime);
    };
    
    const resumeTimer = () => {
        isPaused = false;
        startTimer();
    };
    
    // Event listeners for hover pause
    notification.addEventListener('mouseenter', pauseTimer);
    notification.addEventListener('mouseleave', resumeTimer);
    
    // Start the timer
    startTimer();
}

// Handle Django messages on page load
document.addEventListener('DOMContentLoaded', function() {
    const messages = document.querySelectorAll('.app-message');
    messages.forEach(msg => {
        // Add active class for animation
        setTimeout(() => msg.classList.add('active'), 100);
        
        // Auto dismiss after 5s
        setTimeout(() => {
            msg.classList.remove('active');
            setTimeout(() => msg.remove(), 400);
        }, 5000);
    });
});
