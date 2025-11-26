// Search interactions for landing page
document.addEventListener('DOMContentLoaded', function() {
  // Clear button functionality
  const searchInput = document.getElementById('searchInput');
  const clearBtn = document.getElementById('clearBtn');
  
  if (searchInput && clearBtn) {
    searchInput.addEventListener('input', function() {
      clearBtn.style.display = this.value ? 'flex' : 'none';
    });
    
    clearBtn.addEventListener('click', function() {
      searchInput.value = '';
      this.style.display = 'none';
      searchInput.focus();
    });
  }
  
  // Price slider functionality
  const priceSlider = document.getElementById('priceSlider');
  const priceValue = document.getElementById('priceValue');
  
  if (priceSlider && priceValue) {
    priceSlider.addEventListener('input', function() {
      const value = this.value;
      priceValue.textContent = `$0 - $${value}`;
      
      // Update slider gradient
      const percentage = (value / this.max) * 100;
      this.style.background = `linear-gradient(to right, var(--primary) 0%, var(--primary) ${percentage}%, #e2e8f0 ${percentage}%, #e2e8f0 100%)`;
    });
  }
});
