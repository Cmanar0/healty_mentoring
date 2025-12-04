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
    // Function to update slider appearance
    const updateSlider = function() {
      const value = parseFloat(priceSlider.value);
      const max = parseFloat(priceSlider.max);
      const min = parseFloat(priceSlider.min);
      
      // Calculate percentage based on value (0-100%)
      const percentage = ((value - min) / (max - min)) * 100;
      
      // Update price display
      priceValue.textContent = `$0 - $${value}`;
      
      // The browser positions the thumb center linearly based on the value percentage
      // So we can directly use the percentage for the gradient
      // This ensures perfect synchronization between thumb center and progress bar
      const gradientPercentage = percentage;
      
      // Update slider gradient - synchronized with thumb's center position
      priceSlider.style.background = `linear-gradient(to right, var(--primary) 0%, var(--primary) ${gradientPercentage}%, #e2e8f0 ${gradientPercentage}%, #e2e8f0 100%)`;
    };
    
    // Initialize slider on page load (after a small delay to ensure layout is calculated)
    setTimeout(updateSlider, 0);
    
    // Update on input (while dragging)
    priceSlider.addEventListener('input', updateSlider);
    
    // Also update on change (when released)
    priceSlider.addEventListener('change', updateSlider);
    
    // Update on window resize to recalculate positions
    window.addEventListener('resize', updateSlider);
  }
});
