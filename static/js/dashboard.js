document.addEventListener('DOMContentLoaded', function() {
    // --- Tab Switching Logic ---
    window.switchTab = function(tabName) {
        // Update Tab Buttons
        const buttons = document.querySelectorAll('.tab-btn');
        buttons.forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');

        // Update List Content (Mock Logic for Demo)
        const list = document.getElementById('todo-list');
        if (tabName === 'todo') {
            list.innerHTML = `
                <li class="task-item">
                    <div class="task-check"><i class="fas fa-check"></i></div>
                    <div class="task-content">
                        <span class="task-title">Review Q3 Financials</span>
                        <span class="task-meta">Due Today • Strategy</span>
                    </div>
                </li>
                <li class="task-item">
                    <div class="task-check"><i class="fas fa-check"></i></div>
                    <div class="task-content">
                        <span class="task-title">Draft Team Restructuring Plan</span>
                        <span class="task-meta">Due Tomorrow • Leadership</span>
                    </div>
                </li>
                <li class="task-item">
                    <div class="task-check"><i class="fas fa-check"></i></div>
                    <div class="task-content">
                        <span class="task-title">Prepare Pitch Deck</span>
                        <span class="task-meta">Due Friday • Execution</span>
                    </div>
                </li>
            `;
        } else {
            list.innerHTML = `
                <li class="task-item">
                    <div class="task-check completed"><i class="fas fa-check"></i></div>
                    <div class="task-content">
                        <span class="task-title">Initial Mentor Call</span>
                        <span class="task-meta">Completed Yesterday</span>
                    </div>
                </li>
                <li class="task-item">
                    <div class="task-check completed"><i class="fas fa-check"></i></div>
                    <div class="task-content">
                        <span class="task-title">Define Q4 Goals</span>
                        <span class="task-meta">Completed 2 days ago</span>
                    </div>
                </li>
            `;
        }
    };

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
