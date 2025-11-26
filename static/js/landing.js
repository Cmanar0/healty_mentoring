document.addEventListener('DOMContentLoaded', function() {
  // Initialize AOS (Animate On Scroll)
  AOS.init({
    duration: 800,
    once: true,
    offset: 100
  });

  // Radar Chart Initialization
  const ctx = document.getElementById('lifeBalanceChart').getContext('2d');
  
  // Custom Chart Data
  const data = {
    labels: ['Health', 'Finance', 'Career', 'Relationships', 'Education', 'Fun'],
    datasets: [{
      label: 'Current Balance',
      data: [15, 39, 36, 35, 26, 55],
      fill: true,
      backgroundColor: 'rgba(16, 185, 129, 0.2)',
      borderColor: '#10b981',
      pointBackgroundColor: '#10b981',
      pointBorderColor: '#fff',
      pointHoverBackgroundColor: '#fff',
      pointHoverBorderColor: '#10b981'
    }, {
      label: 'Goal',
      data: [85, 80, 95, 90, 85, 80],
      fill: true,
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      borderColor: '#3b82f6',
      pointBackgroundColor: '#3b82f6',
      pointBorderColor: '#fff',
      pointHoverBackgroundColor: '#fff',
      pointHoverBorderColor: '#3b82f6',
      borderDash: [5, 5]
    }]
  };

  const config = {
    type: 'radar',
    data: data,
    options: {
      elements: {
        line: { borderWidth: 3 }
      },
      scales: {
        r: {
          angleLines: { color: 'rgba(0, 0, 0, 0.1)' },
          grid: { color: 'rgba(0, 0, 0, 0.1)' },
          pointLabels: {
            font: {
              family: "'Outfit', sans-serif",
              size: 14,
              weight: '600'
            },
            color: '#1e293b'
          },
          ticks: { display: false }
        }
      },
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            font: { family: "'Inter', sans-serif" },
            usePointStyle: true
          }
        }
      }
    }
  };

  new Chart(ctx, config);

  // Email Obfuscation for Footer
  const contactLink = document.getElementById('contact-link');
  if (contactLink) {
    contactLink.addEventListener('click', function(e) {
      e.preventDefault();
      const user = 'info';
      const domain = 'healthymentoring.com';
      window.location.href = 'mailto:' + user + '@' + domain;
    });
  }
});
