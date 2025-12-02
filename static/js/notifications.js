/**
 * Unified Notification System
 * Usage: showNotification(message, type)
 * Types: 'note', 'warning', 'error', 'success'
 */

function showNotification(message, type = 'note') {
    // Remove existing notification if any
    const existingNotification = document.querySelector('.app-notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `app-notification app-notification-${type}`;
    notification.textContent = message;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Show notification
    setTimeout(() => {
        notification.classList.add('active');
    }, 10);
    
    // Hide and remove after 4 seconds
    setTimeout(() => {
        notification.classList.remove('active');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 4000);
}

