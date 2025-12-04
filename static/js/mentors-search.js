// Mentors page search and filter functionality
document.addEventListener('DOMContentLoaded', function() {
    // Get predefined data
    const predefinedCategoriesData = document.getElementById('predefinedCategoriesData');
    const predefinedLanguagesData = document.getElementById('predefinedLanguagesData');
    
    const predefinedCategories = predefinedCategoriesData ? JSON.parse(predefinedCategoriesData.textContent) : [];
    const predefinedLanguages = predefinedLanguagesData ? JSON.parse(predefinedLanguagesData.textContent) : [];
    
    // Elements
    const searchInput = document.getElementById('searchInput');
    const mentorSuggestions = document.getElementById('mentorSuggestions');
    const clearBtn = document.getElementById('clearBtn');
    const priceSlider = document.getElementById('priceSlider');
    const priceValue = document.getElementById('priceValue');
    const firstSessionFree = document.getElementById('firstSessionFree');
    
    // Filter Inputs
    const categoryInput = document.getElementById('categoryInput');
    const categorySuggestions = document.getElementById('categorySuggestions');
    const categoryValue = document.getElementById('categoryValue');
    
    const languageInput = document.getElementById('languageInput');
    const languageSuggestions = document.getElementById('languageSuggestions');
    const languageValue = document.getElementById('languageValue');
    
    
    // --- Autocomplete Logic ---
    
    // Render flag function - same as in profile template
    function renderFlag(item) {
        // For languages: use flag_code if available, otherwise use id
        const flagCode = item.flag_code || item.id;
        if (flagCode) {
            // Use flag-icon-css if flag_code/id is available
            return `<span class="fi fi-${flagCode.toLowerCase()}" style="margin-right: 6px; vertical-align: middle;"></span>`;
        } else if (item.flag) {
            // Fallback to emoji
            return item.flag + ' ';
        }
        return '';
    }
    
    function setupAutocomplete(input, suggestionsContainer, data, valueInput, onSelect) {
        if (!input || !suggestionsContainer) return;
        
        input.addEventListener('input', function() {
            const query = this.value.toLowerCase();
            const matches = data.filter(item => item.name.toLowerCase().includes(query));
            
            suggestionsContainer.innerHTML = '';
            
            if (matches.length > 0) {
                matches.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'suggestion-item';
                    
                    // Handle flag for languages - use renderFlag function
                    let content = item.name;
                    if (item.flag_code || item.flag) {
                        content = renderFlag(item) + item.name;
                    }
                    
                    div.innerHTML = content;
                    
                    div.addEventListener('click', function() {
                        input.value = item.name;
                        if (valueInput) valueInput.value = item.id;
                        suggestionsContainer.style.display = 'none';
                        if (onSelect) onSelect(item);
                    });
                    suggestionsContainer.appendChild(div);
                });
                suggestionsContainer.style.display = 'block';
                suggestionsContainer.style.maxHeight = '300px';
                suggestionsContainer.style.overflowY = 'auto';
            } else {
                suggestionsContainer.style.display = 'none';
            }
        });
        
        // Show all on focus if empty
        input.addEventListener('focus', function() {
            if (this.value.trim() === '') {
                // Trigger input event to show all
                this.dispatchEvent(new Event('input'));
            }
        });
        
        // Hide on click outside
        document.addEventListener('click', function(e) {
            if (!input.contains(e.target) && !suggestionsContainer.contains(e.target)) {
                suggestionsContainer.style.display = 'none';
            }
        });
        
        // Clear value if input cleared
        input.addEventListener('change', function() {
            if (this.value.trim() === '') {
                if (valueInput) valueInput.value = '';
                if (onSelect) onSelect(null);
            }
        });
    }
    
    // Initialize Category Autocomplete
    setupAutocomplete(categoryInput, categorySuggestions, predefinedCategories, categoryValue, performSearch);
    
    // Initialize Language Autocomplete
    setupAutocomplete(languageInput, languageSuggestions, predefinedLanguages, languageValue, performSearch);
    
    // --- Existing Search Logic ---
    
    const updateSlider = function() {
      if (!priceSlider || !priceValue) return;
      const value = parseFloat(priceSlider.value);
      const max = parseFloat(priceSlider.max);
      const min = parseFloat(priceSlider.min);
      const percentage = ((value - min) / (max - min)) * 100;
      
      // Show "200+" when at max, otherwise show range
      if (value >= max) {
        priceValue.textContent = '$0 - $200+';
      } else {
        priceValue.textContent = `$0 - $${Math.round(value)}`;
      }
      
      priceSlider.style.background = `linear-gradient(to right, var(--primary) 0%, var(--primary) ${percentage}%, #e2e8f0 ${percentage}%, #e2e8f0 100%)`;
    };
    
    // Load price from URL parameters on page load
    function loadPriceFromURL() {
        if (!priceSlider) return;
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('price')) {
            const price = parseFloat(urlParams.get('price'));
            if (!isNaN(price)) {
                priceSlider.value = price;
                // Update slider display after setting value
                // Use setTimeout to ensure the value is set before updating
                setTimeout(() => {
                    updateSlider();
                }, 0);
            }
        }
    }
    
    if (priceSlider) {
      // Load price from URL first
      loadPriceFromURL();
      
      // Also update on initial load (in case no URL param)
      setTimeout(updateSlider, 0);
      
      // Then set up event listeners
      priceSlider.addEventListener('input', updateSlider);
      priceSlider.addEventListener('change', () => {
          updateSlider();
          performSearch();
      });
      window.addEventListener('resize', updateSlider);
    }
    
    // Mentor Name Search
    let mentorSearchTimer;
    function searchMentors(query) {
      if (query.length < 2) {
        if (mentorSuggestions) mentorSuggestions.style.display = 'none';
        return;
      }
      const searchUrl = document.querySelector('[data-search-url]')?.dataset.searchUrl || '/mentors/search/';
      fetch(`${searchUrl}?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
          displayMentorSuggestions(data.suggestions);
        })
        .catch(error => {
          console.error('Error searching mentors:', error);
          if (mentorSuggestions) mentorSuggestions.style.display = 'none';
        });
    }
    
    function displayMentorSuggestions(suggestions) {
      if (!mentorSuggestions) return;
      if (suggestions.length === 0) {
        mentorSuggestions.style.display = 'none';
        return;
      }
      mentorSuggestions.innerHTML = '';
      suggestions.forEach((mentor, index) => {
        const item = document.createElement('div');
        item.className = 'suggestion-item mentor-suggestion-item';
        
        const avatarHtml = mentor.avatar_url 
          ? `<img src="${mentor.avatar_url}" alt="${mentor.name}" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover;">`
          : `<div style="width: 32px; height: 32px; border-radius: 50%; background: #e2e8f0; display: flex; align-items: center; justify-content: center; color: #94a3b8; font-size: 0.8rem;">${mentor.name.charAt(0)}</div>`;
        
        item.innerHTML = `
          <div style="display: flex; align-items: center; gap: 12px; width: 100%;">
            ${avatarHtml}
            <div style="flex: 1; min-width: 0;">
              <div style="font-weight: 600; color: var(--text-dark); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${mentor.name}</div>
              <div style="font-size: 0.85rem; color: var(--text-light); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${mentor.mentor_type}</div>
            </div>
          </div>
        `;
        
        item.addEventListener('click', function() {
          if (searchInput) {
            searchInput.value = mentor.name;
            mentorSuggestions.style.display = 'none';
            performSearch();
          }
        });
        mentorSuggestions.appendChild(item);
      });
      mentorSuggestions.style.display = 'block';
      mentorSuggestions.style.maxHeight = '300px';
      mentorSuggestions.style.overflowY = 'auto';
    }
    
    if (searchInput) {
      searchInput.addEventListener('input', function() {
        clearTimeout(mentorSearchTimer);
        const query = this.value.trim();
        if (clearBtn) clearBtn.style.display = query ? 'flex' : 'none';
        mentorSearchTimer = setTimeout(() => {
          if (query.length >= 2) searchMentors(query);
          else if (mentorSuggestions) mentorSuggestions.style.display = 'none';
        }, 300);
      });
      
      searchInput.addEventListener('focus', function() {
        if (this.value.trim().length >= 2) searchMentors(this.value.trim());
      });
      
      document.addEventListener('click', function(event) {
        if (!searchInput.contains(event.target) && (!mentorSuggestions || !mentorSuggestions.contains(event.target))) {
          if (mentorSuggestions) mentorSuggestions.style.display = 'none';
        }
      });
    }
    
    if (clearBtn) {
      clearBtn.addEventListener('click', function() {
        if (searchInput) {
          searchInput.value = '';
          if (mentorSuggestions) mentorSuggestions.style.display = 'none';
          clearBtn.style.display = 'none';
          performSearch();
        }
      });
    }

    // First Session Free toggle with status text update
    const firstSessionStatusText = document.getElementById('firstSessionStatusText');
    if (firstSessionFree) {
      // Update status text on change
      firstSessionFree.addEventListener('change', function() {
        if (firstSessionStatusText) {
          firstSessionStatusText.textContent = this.checked ? 'Enabled' : 'Disabled';
        }
        performSearch();
      });
    }
    
    function performSearch() {
      const params = new URLSearchParams();
      if (searchInput && searchInput.value.trim()) params.append('q', searchInput.value.trim());
      if (categoryValue && categoryValue.value) params.append('category', categoryValue.value);
      if (priceSlider) params.append('price', priceSlider.value);
      if (languageValue && languageValue.value) params.append('language', languageValue.value);
      if (firstSessionFree && firstSessionFree.checked) params.append('first_session_free', 'true');
      
      window.location.href = window.location.pathname + "?" + params.toString();
    };
});
