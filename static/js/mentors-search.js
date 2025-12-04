// Mentors page search and filter functionality
document.addEventListener('DOMContentLoaded', function() {
    // Get predefined data
    const predefinedCategoriesData = document.getElementById('predefinedCategoriesData');
    const predefinedLanguagesData = document.getElementById('predefinedLanguagesData');
    const commonTimezonesData = document.getElementById('commonTimezonesData');
    const predefinedCategories = predefinedCategoriesData ? JSON.parse(predefinedCategoriesData.textContent) : [];
    const predefinedLanguages = predefinedLanguagesData ? JSON.parse(predefinedLanguagesData.textContent) : [];
    const commonTimezones = commonTimezonesData ? JSON.parse(commonTimezonesData.textContent) : [];
    
    // Elements
    const searchInput = document.getElementById('searchInput');
    const mentorSuggestions = document.getElementById('mentorSuggestions');
    const categoryInput = document.getElementById('categoryInput');
    const categoryValue = document.getElementById('categoryValue');
    const categorySuggestions = document.getElementById('categorySuggestions');
    const languageInput = document.getElementById('languageInput');
    const languageValue = document.getElementById('languageValue');
    const languageSuggestions = document.getElementById('languageSuggestions');
    const priceSlider = document.getElementById('priceSlider');
    const priceValue = document.getElementById('priceValue');
    const firstSessionFree = document.getElementById('firstSessionFree');
    const timezoneMinInput = document.getElementById('timezoneMinInput');
    const timezoneMinValue = document.getElementById('timezoneMinValue');
    const timezoneMinSuggestions = document.getElementById('timezoneMinSuggestions');
    const timezoneMaxInput = document.getElementById('timezoneMaxInput');
    const timezoneMaxValue = document.getElementById('timezoneMaxValue');
    const timezoneMaxSuggestions = document.getElementById('timezoneMaxSuggestions');
    const timezoneRangePlus = document.getElementById('timezoneRangePlus');
    const timezoneRangeMinus = document.getElementById('timezoneRangeMinus');
    const clearBtn = document.getElementById('clearBtn');
    
    // Selected values (single selection for category and language)
    let selectedCategory = categoryValue ? categoryValue.value : '';
    let selectedLanguage = languageValue ? languageValue.value : '';
    let selectedTimezoneMin = timezoneMinValue ? timezoneMinValue.value : '';
    let selectedTimezoneMax = timezoneMaxValue ? timezoneMaxValue.value : '';
    
    // Debounce timers
    let mentorSearchTimer;
    let categoryDebounceTimer;
    let languageDebounceTimer;
    let timezoneMinDebounceTimer;
    let timezoneMaxDebounceTimer;
    
    // Load filters from URL parameters on page load
    function loadFiltersFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        
        // Load search query
        if (urlParams.has('q') && searchInput) {
            const query = urlParams.get('q');
            searchInput.value = query;
            if (clearBtn) clearBtn.style.display = query ? 'flex' : 'none';
        }
        
        // Load category
        if (urlParams.has('category')) {
            const categoryId = urlParams.get('category');
            selectedCategory = categoryId;
            if (categoryValue) categoryValue.value = categoryId;
            
            // Find category name and set it in the input
            const category = predefinedCategories.find(cat => cat.id === categoryId);
            if (category && categoryInput) {
                categoryInput.value = category.name;
            }
        }
        
        // Load language
        if (urlParams.has('language')) {
            const languageId = urlParams.get('language');
            selectedLanguage = languageId;
            if (languageValue) languageValue.value = languageId;
            
            // Find language name and set it in the input
            const language = predefinedLanguages.find(lang => lang.id === languageId);
            if (language && languageInput) {
                languageInput.value = language.name;
            }
        }
        
        // Load price slider
        if (urlParams.has('price') && priceSlider) {
            const price = urlParams.get('price');
            priceSlider.value = price;
            updateSlider();
        }
        
        // Load first session free
        if (urlParams.has('first_session_free') && firstSessionFree) {
            firstSessionFree.checked = urlParams.get('first_session_free') === 'true';
        }
        
        // Load timezone min
        if (urlParams.has('timezone_min')) {
            const tzMinId = urlParams.get('timezone_min');
            selectedTimezoneMin = tzMinId;
            if (timezoneMinValue) timezoneMinValue.value = tzMinId;
            
            // Find timezone name and set it in the input
            const tzMin = commonTimezones.find(tz => tz.id === tzMinId);
            if (tzMin && timezoneMinInput) {
                timezoneMinInput.value = `${tzMin.name} (${tzMin.offset})`;
            }
        }
        
        // Load timezone max
        if (urlParams.has('timezone_max')) {
            const tzMaxId = urlParams.get('timezone_max');
            selectedTimezoneMax = tzMaxId;
            if (timezoneMaxValue) timezoneMaxValue.value = tzMaxId;
            
            // Find timezone name and set it in the input
            const tzMax = commonTimezones.find(tz => tz.id === tzMaxId);
            if (tzMax && timezoneMaxInput) {
                timezoneMaxInput.value = `${tzMax.name} (${tzMax.offset})`;
            }
        }
    }
    
    // Function to update slider appearance
    const updateSlider = function() {
      if (!priceSlider || !priceValue) return;
      const value = parseFloat(priceSlider.value);
      const max = parseFloat(priceSlider.max);
      const min = parseFloat(priceSlider.min);
      const percentage = ((value - min) / (max - min)) * 100;
      priceValue.textContent = `$0 - $${Math.round(value)}`;
      priceSlider.style.background = `linear-gradient(to right, var(--primary) 0%, var(--primary) ${percentage}%, #e2e8f0 ${percentage}%, #e2e8f0 100%)`;
    };
    
    if (priceSlider) {
      setTimeout(updateSlider, 0);
      priceSlider.addEventListener('input', updateSlider);
      priceSlider.addEventListener('change', updateSlider);
      window.addEventListener('resize', updateSlider);
    }
    
    // Call on page load to sync filters with URL parameters
    loadFiltersFromURL();
    
    // Mentor name search with suggestions
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
        if (index === 0) item.classList.add('first-item');
        if (index === suggestions.length - 1) item.classList.add('last-item');
        
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
    
    if (searchInput && mentorSuggestions) {
      searchInput.addEventListener('input', function() {
        clearTimeout(mentorSearchTimer);
        const query = this.value.trim();
        if (clearBtn) clearBtn.style.display = query ? 'flex' : 'none';
        
        mentorSearchTimer = setTimeout(() => {
          if (query.length >= 2) {
            searchMentors(query);
          } else {
            mentorSuggestions.style.display = 'none';
          }
        }, 300);
      });
      
      searchInput.addEventListener('focus', function() {
        if (this.value.trim().length >= 2) {
          searchMentors(this.value.trim());
        }
      });
      
      document.addEventListener('click', function(event) {
        if (!searchInput.contains(event.target) && !mentorSuggestions.contains(event.target)) {
          mentorSuggestions.style.display = 'none';
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
    
    // Category filter (single selection)
    function filterCategorySuggestions(query) {
      const filtered = predefinedCategories.filter(cat => 
        cat.name.toLowerCase().includes(query.toLowerCase())
      );
      displayCategorySuggestions(filtered);
    }
    
    function displayCategorySuggestions(suggestions) {
      if (!categorySuggestions) return;
      if (suggestions.length === 0) {
        categorySuggestions.style.display = 'none';
        return;
      }
      
      categorySuggestions.innerHTML = '';
      suggestions.forEach((cat, index) => {
        const item = document.createElement('div');
        item.className = 'suggestion-item';
        if (index === 0) item.classList.add('first-item');
        if (index === suggestions.length - 1) item.classList.add('last-item');
        item.textContent = cat.name;
        item.addEventListener('click', function() {
          selectedCategory = cat.id;
          if (categoryInput) categoryInput.value = cat.name;
          if (categoryValue) categoryValue.value = cat.id;
          categorySuggestions.style.display = 'none';
          performSearch();
        });
        categorySuggestions.appendChild(item);
      });
      
      categorySuggestions.style.display = 'block';
      categorySuggestions.style.maxHeight = '300px';
      categorySuggestions.style.overflowY = 'auto';
    }
    
    if (categoryInput && categorySuggestions) {
      categoryInput.addEventListener('focus', function() {
        const query = this.value.trim();
        if (query.length > 0) {
          filterCategorySuggestions(query);
        } else {
          displayCategorySuggestions(predefinedCategories);
        }
      });
      
      categoryInput.addEventListener('input', function() {
        clearTimeout(categoryDebounceTimer);
        const query = this.value.trim();
        categoryDebounceTimer = setTimeout(() => {
          if (query.length > 0) {
            filterCategorySuggestions(query);
          } else {
            displayCategorySuggestions(predefinedCategories);
          }
        }, 200);
      });
      
      categoryInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          const query = this.value.trim();
          const cat = predefinedCategories.find(c => c.name.toLowerCase() === query.toLowerCase());
          if (cat) {
            selectedCategory = cat.id;
            categoryInput.value = cat.name;
            if (categoryValue) categoryValue.value = cat.id;
            categorySuggestions.style.display = 'none';
            performSearch();
          }
        }
      });
      
      document.addEventListener('click', function(event) {
        if (!categoryInput.contains(event.target) && !categorySuggestions.contains(event.target)) {
          categorySuggestions.style.display = 'none';
        }
      });
    }
    
    // Language filter (single selection)
    function filterLanguageSuggestions(query) {
      const filtered = predefinedLanguages.filter(lang => 
        lang.name.toLowerCase().includes(query.toLowerCase())
      );
      displayLanguageSuggestions(filtered);
    }
    
    function displayLanguageSuggestions(suggestions) {
      if (!languageSuggestions) return;
      if (suggestions.length === 0) {
        languageSuggestions.style.display = 'none';
        return;
      }
      
      languageSuggestions.innerHTML = '';
      suggestions.forEach((lang, index) => {
        const item = document.createElement('div');
        item.className = 'suggestion-item';
        if (index === 0) item.classList.add('first-item');
        if (index === suggestions.length - 1) item.classList.add('last-item');
        item.innerHTML = `<span class="flag-icon fi fi-${lang.flag_code}"></span> ${lang.name}`;
        item.addEventListener('click', function() {
          selectedLanguage = lang.id;
          if (languageInput) languageInput.value = lang.name;
          if (languageValue) languageValue.value = lang.id;
          languageSuggestions.style.display = 'none';
          performSearch();
        });
        languageSuggestions.appendChild(item);
      });
      
      languageSuggestions.style.display = 'block';
      languageSuggestions.style.maxHeight = '300px';
      languageSuggestions.style.overflowY = 'auto';
    }
    
    if (languageInput && languageSuggestions) {
      languageInput.addEventListener('focus', function() {
        const query = this.value.trim();
        if (query.length > 0) {
          filterLanguageSuggestions(query);
        } else {
          displayLanguageSuggestions(predefinedLanguages);
        }
      });
      
      languageInput.addEventListener('input', function() {
        clearTimeout(languageDebounceTimer);
        const query = this.value.trim();
        languageDebounceTimer = setTimeout(() => {
          if (query.length > 0) {
            filterLanguageSuggestions(query);
          } else {
            displayLanguageSuggestions(predefinedLanguages);
          }
        }, 200);
      });
      
      languageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          const query = this.value.trim();
          const lang = predefinedLanguages.find(l => l.name.toLowerCase() === query.toLowerCase());
          if (lang) {
            selectedLanguage = lang.id;
            languageInput.value = lang.name;
            if (languageValue) languageValue.value = lang.id;
            languageSuggestions.style.display = 'none';
            performSearch();
          }
        }
      });
      
      document.addEventListener('click', function(event) {
        if (!languageInput.contains(event.target) && !languageSuggestions.contains(event.target)) {
          languageSuggestions.style.display = 'none';
        }
      });
    }
    
    // Timezone filter functions
    function filterTimezoneSuggestions(query, suggestionsContainer, isMin) {
      const filtered = commonTimezones.filter(tz => 
        tz.name.toLowerCase().includes(query.toLowerCase()) ||
        tz.region.toLowerCase().includes(query.toLowerCase())
      );
      displayTimezoneSuggestions(filtered, suggestionsContainer, isMin);
    }
    
    function displayTimezoneSuggestions(suggestions, suggestionsContainer, isMin) {
      if (!suggestionsContainer) return;
      if (suggestions.length === 0) {
        suggestionsContainer.style.display = 'none';
        return;
      }
      
      suggestionsContainer.innerHTML = '';
      suggestions.forEach((tz, index) => {
        const item = document.createElement('div');
        item.className = 'suggestion-item';
        if (index === 0) item.classList.add('first-item');
        if (index === suggestions.length - 1) item.classList.add('last-item');
        item.textContent = `${tz.name} (${tz.offset})`;
        item.addEventListener('click', function() {
          if (isMin) {
            selectedTimezoneMin = tz.id;
            if (timezoneMinInput) timezoneMinInput.value = `${tz.name} (${tz.offset})`;
            if (timezoneMinValue) timezoneMinValue.value = tz.id;
          } else {
            selectedTimezoneMax = tz.id;
            if (timezoneMaxInput) timezoneMaxInput.value = `${tz.name} (${tz.offset})`;
            if (timezoneMaxValue) timezoneMaxValue.value = tz.id;
          }
          suggestionsContainer.style.display = 'none';
          performSearch();
        });
        suggestionsContainer.appendChild(item);
      });
      
      suggestionsContainer.style.display = 'block';
      suggestionsContainer.style.maxHeight = '300px';
      suggestionsContainer.style.overflowY = 'auto';
    }
    
    if (timezoneMinInput && timezoneMinSuggestions) {
      timezoneMinInput.addEventListener('focus', function() {
        const query = this.value.trim();
        if (query.length > 0) {
          filterTimezoneSuggestions(query, timezoneMinSuggestions, true);
        } else {
          displayTimezoneSuggestions(commonTimezones, timezoneMinSuggestions, true);
        }
      });
      
      timezoneMinInput.addEventListener('input', function() {
        clearTimeout(timezoneMinDebounceTimer);
        const query = this.value.trim();
        timezoneMinDebounceTimer = setTimeout(() => {
          if (query.length > 0) {
            filterTimezoneSuggestions(query, timezoneMinSuggestions, true);
          } else {
            displayTimezoneSuggestions(commonTimezones, timezoneMinSuggestions, true);
          }
        }, 200);
      });
      
      document.addEventListener('click', function(event) {
        if (!timezoneMinInput.contains(event.target) && !timezoneMinSuggestions.contains(event.target)) {
          timezoneMinSuggestions.style.display = 'none';
        }
      });
    }
    
    if (timezoneMaxInput && timezoneMaxSuggestions) {
      timezoneMaxInput.addEventListener('focus', function() {
        const query = this.value.trim();
        if (query.length > 0) {
          filterTimezoneSuggestions(query, timezoneMaxSuggestions, false);
        } else {
          displayTimezoneSuggestions(commonTimezones, timezoneMaxSuggestions, false);
        }
      });
      
      timezoneMaxInput.addEventListener('input', function() {
        clearTimeout(timezoneMaxDebounceTimer);
        const query = this.value.trim();
        timezoneMaxDebounceTimer = setTimeout(() => {
          if (query.length > 0) {
            filterTimezoneSuggestions(query, timezoneMaxSuggestions, false);
          } else {
            displayTimezoneSuggestions(commonTimezones, timezoneMaxSuggestions, false);
          }
        }, 200);
      });
      
      document.addEventListener('click', function(event) {
        if (!timezoneMaxInput.contains(event.target) && !timezoneMaxSuggestions.contains(event.target)) {
          timezoneMaxSuggestions.style.display = 'none';
        }
      });
    }
    
    // Timezone range +/- buttons
    if (timezoneRangePlus) {
      timezoneRangePlus.addEventListener('click', function() {
        selectedTimezoneMin = '';
        selectedTimezoneMax = '';
        if (timezoneMinInput) timezoneMinInput.value = '';
        if (timezoneMaxInput) timezoneMaxInput.value = '';
        if (timezoneMinValue) timezoneMinValue.value = '';
        if (timezoneMaxValue) timezoneMaxValue.value = '';
        performSearch();
      });
    }
    
    if (timezoneRangeMinus) {
      timezoneRangeMinus.addEventListener('click', function() {
        if (selectedTimezoneMin && !selectedTimezoneMax) {
          selectedTimezoneMax = selectedTimezoneMin;
          const tz = commonTimezones.find(t => t.id === selectedTimezoneMin);
          if (tz) {
            if (timezoneMaxInput) timezoneMaxInput.value = `${tz.name} (${tz.offset})`;
            if (timezoneMaxValue) timezoneMaxValue.value = tz.id;
          }
        } else if (!selectedTimezoneMin && selectedTimezoneMax) {
          selectedTimezoneMin = selectedTimezoneMax;
          const tz = commonTimezones.find(t => t.id === selectedTimezoneMax);
          if (tz) {
            if (timezoneMinInput) timezoneMinInput.value = `${tz.name} (${tz.offset})`;
            if (timezoneMinValue) timezoneMinValue.value = tz.id;
          }
        }
        performSearch();
      });
    }
    
    // Handle Search Submission
    let performSearch = function() {
      const params = new URLSearchParams();
      
      if (searchInput && searchInput.value.trim()) {
        params.append('q', searchInput.value.trim());
      }
      if (selectedCategory) {
        params.append('category', selectedCategory);
      }
      if (priceSlider) {
        params.append('price', priceSlider.value);
      }
      if (selectedLanguage) {
        params.append('language', selectedLanguage);
      }
      if (firstSessionFree && firstSessionFree.checked) {
        params.append('first_session_free', 'true');
      }
      if (selectedTimezoneMin) {
        params.append('timezone_min', selectedTimezoneMin);
      }
      if (selectedTimezoneMax) {
        params.append('timezone_max', selectedTimezoneMax);
      }
      
      window.location.href = window.location.pathname + "?" + params.toString();
    };

    const searchBtn = document.querySelector('.search-btn');
    if (searchBtn) {
      searchBtn.addEventListener('click', function(e) {
        e.preventDefault();
        performSearch();
      });
    }

    if (searchInput) {
      searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          performSearch();
        }
      });
    }
    
    // Auto-submit on filter changes
    if (categoryInput) {
      categoryInput.addEventListener('blur', function() {
        setTimeout(() => performSearch(), 200);
      });
    }
    
    if (languageInput) {
      languageInput.addEventListener('blur', function() {
        setTimeout(() => performSearch(), 200);
      });
    }
    
    if (firstSessionFree) {
      firstSessionFree.addEventListener('change', performSearch);
    }
    
    if (priceSlider) {
      priceSlider.addEventListener('change', performSearch);
    }
    
    // Infinite scroll functionality
    const currentPageData = document.getElementById('currentPageData');
    const hasNextData = document.getElementById('hasNextData');
    let currentPage = currentPageData ? JSON.parse(currentPageData.textContent) : 1;
    let isLoading = false;
    let hasMore = hasNextData ? JSON.parse(hasNextData.textContent) : false;
    const mentorsContainer = document.getElementById('mentorsContainer');
    const mentorsLoading = document.getElementById('mentorsLoading');
    const mentorsEnd = document.getElementById('mentorsEnd');
    
    function loadMoreMentors() {
      if (isLoading || !hasMore) return;
      
      isLoading = true;
      if (mentorsLoading) mentorsLoading.style.display = 'block';
      
      const nextPage = currentPage + 1;
      const params = new URLSearchParams();
      
      if (searchInput && searchInput.value.trim()) {
        params.append('q', searchInput.value.trim());
      }
      if (selectedCategory) {
        params.append('category', selectedCategory);
      }
      if (priceSlider) {
        params.append('price', priceSlider.value);
      }
      if (selectedLanguage) {
        params.append('language', selectedLanguage);
      }
      if (firstSessionFree && firstSessionFree.checked) {
        params.append('first_session_free', 'true');
      }
      if (selectedTimezoneMin) {
        params.append('timezone_min', selectedTimezoneMin);
      }
      if (selectedTimezoneMax) {
        params.append('timezone_max', selectedTimezoneMax);
      }
      params.append('page', nextPage);
      
      const loadMoreUrl = document.querySelector('script[data-load-more-url]')?.dataset.loadMoreUrl || '/mentors/load-more/';
      
      fetch(`${loadMoreUrl}?${params.toString()}`)
        .then(response => response.json())
        .then(data => {
          if (data.mentors && data.mentors.length > 0) {
            // Append new mentors to container
            data.mentors.forEach(mentor => {
              const mentorCard = createMentorCard(mentor);
              if (mentorsContainer) mentorsContainer.appendChild(mentorCard);
            });
            
            currentPage = data.page;
            hasMore = data.has_next;
            
            if (!hasMore && mentorsEnd) {
              mentorsEnd.style.display = 'block';
            }
          } else {
            hasMore = false;
            if (mentorsEnd) mentorsEnd.style.display = 'block';
          }
          
          isLoading = false;
          if (mentorsLoading) mentorsLoading.style.display = 'none';
        })
        .catch(error => {
          console.error('Error loading more mentors:', error);
          isLoading = false;
          if (mentorsLoading) mentorsLoading.style.display = 'none';
        });
    }
    
    function createMentorCard(mentor) {
      const card = document.createElement('div');
      card.className = 'mentor-card';
      card.setAttribute('data-aos', 'fade-up');
      card.setAttribute('data-mentor-id', mentor.id);
      
      const avatarHtml = mentor.avatar_url 
        ? `<img src="${mentor.avatar_url}" alt="${mentor.first_name} ${mentor.last_name}">`
        : `<img src="https://i.pravatar.cc/150?img=${mentor.id}" alt="${mentor.first_name} ${mentor.last_name}">`;
      
      const quoteHtml = mentor.quote ? `<p class="mentor-motto">"${mentor.quote}"</p>` : '';
      const bioHtml = mentor.bio ? `<p class="mentor-bio">${mentor.bio.split(' ').slice(0, 30).join(' ')}${mentor.bio.split(' ').length > 30 ? '...' : ''}</p>` : '';
      
      const tagsHtml = mentor.tags && mentor.tags.length > 0
        ? `<div class="mentor-tags">${mentor.tags.slice(0, 5).map(tag => `<span class="mentor-tag">${tag}</span>`).join('')}</div>`
        : '';
      
      const priceHtml = mentor.price_per_hour
        ? `<p class="mentor-price">$${Math.round(mentor.price_per_hour)}<span>/session</span></p>`
        : `<p class="mentor-price">Contact<span> for pricing</span></p>`;
      
      card.innerHTML = `
        <div class="mentor-header-content">
          <div class="mentor-avatar">
            ${avatarHtml}
          </div>
          <div class="mentor-title">
            <h4>${mentor.first_name} ${mentor.last_name}</h4>
            <p class="mentor-specialty">${mentor.mentor_type || 'Mentor'}</p>
          </div>
        </div>
        <div class="mentor-details">
          ${quoteHtml}
          ${bioHtml}
          ${tagsHtml}
        </div>
        <div class="mentor-footer">
          ${priceHtml}
          <a href="/mentor/${mentor.id}/" class="btn-mentor">View Profile</a>
        </div>
      `;
      
      return card;
    }
    
    // Scroll detection for infinite scroll
    let scrollTimeout;
    window.addEventListener('scroll', function() {
      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(function() {
        // Check if user is near bottom (within 300px)
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const windowHeight = window.innerHeight;
        const documentHeight = document.documentElement.scrollHeight;
        
        if (scrollTop + windowHeight >= documentHeight - 300) {
          loadMoreMentors();
        }
      }, 100);
    });
    
    // Reset pagination when filters change
    const originalPerformSearch = performSearch;
    performSearch = function() {
      currentPage = 1;
      hasMore = true;
      if (mentorsEnd) mentorsEnd.style.display = 'none';
      originalPerformSearch();
    };
});

