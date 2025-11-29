document.addEventListener('DOMContentLoaded', function() {
    
    // --- Dropdown Logic ---
    window.toggleDropdown = function(btn) {
        // Close all other dropdowns first
        const allMenus = document.querySelectorAll('.dropdown-menu');
        const currentMenu = btn.nextElementSibling;
        
        allMenus.forEach(menu => {
            if (menu !== currentMenu) {
                menu.classList.remove('show');
            }
        });
        
        // Toggle current
        currentMenu.classList.toggle('show');
        
        // Prevent event bubbling
        event.stopPropagation();
    };

    // Close dropdowns when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.dropdown')) {
            document.querySelectorAll('.dropdown-menu').forEach(menu => {
                menu.classList.remove('show');
            });
        }
    });

    // --- Task Completion Logic ---
    window.toggleTask = function(btn) {
        btn.classList.toggle('completed');
        // In a real app, this would send an AJAX request
    };

    // --- Tab Switching Logic (Demo) ---
    // (Kept simple for now, can be expanded)
    
    // --- Radar Chart Initialization ---
    const ctx = document.getElementById('startupRadarChart');
    if (ctx) {
        new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['Product', 'Market', 'Team', 'Finance', 'Legal', 'Traction'],
                datasets: [{
                    label: 'Current Status',
                    data: [65, 59, 90, 81, 56, 55],
                    fill: true,
                    backgroundColor: 'rgba(16, 185, 129, 0.2)',
                    borderColor: '#10b981',
                    pointBackgroundColor: '#10b981',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#10b981'
                }, {
                    label: 'Goal',
                    data: [80, 80, 95, 90, 80, 85],
                    fill: true,
                    backgroundColor: 'rgba(59, 130, 246, 0.2)',
                    borderColor: '#3b82f6',
                    pointBackgroundColor: '#3b82f6',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#3b82f6'
                }]
            },
            options: {
                elements: {
                    line: { borderWidth: 2 }
                },
                scales: {
                    r: {
                        angleLines: { display: true, color: '#e2e8f0' },
                        grid: { color: '#e2e8f0' },
                        pointLabels: {
                            font: { size: 12, family: "'Inter', sans-serif" },
                            color: '#64748b'
                        },
                        ticks: { display: false, maxTicksLimit: 5 }
                    }
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            font: { family: "'Inter', sans-serif" }
                        }
                    }
                },
                maintainAspectRatio: false
            }
        });
    }
});
