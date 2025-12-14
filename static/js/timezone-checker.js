/**
 * Timezone Checker - New Logic
 * 
 * Three fields:
 * 1. detected_timezone - Browser-detected timezone, updated on each page load
 * 2. selected_timezone - User's selected/preferred timezone
 * 3. confirmed_timezone_mismatch - Boolean, true if user confirmed they want different timezone
 * 
 * Logic:
 * - On every page load, detect browser timezone
 * - If different from detected_timezone in DB, update it
 * - If selected_timezone == detected_timezone: All good, set confirmed_timezone_mismatch = False
 * - If selected_timezone != detected_timezone:
 *   - If confirmed_timezone_mismatch == False: Show popup
 *   - If confirmed_timezone_mismatch == True: Don't show popup (user already confirmed)
 */

(function() {
    'use strict';

    // Get current UTC offset for a timezone (handles DST automatically)
    // Uses JavaScript's native timezone support - IANA timezones already handle DST
    function getCurrentTimezoneOffset(ianaId) {
        try {
            const now = new Date();
            
            // Use Intl.DateTimeFormat to get the timezone offset
            // This automatically handles DST based on the current date
            const formatter = new Intl.DateTimeFormat('en', {
                timeZone: ianaId,
                timeZoneName: 'longOffset'
            });
            
            const parts = formatter.formatToParts(now);
            const offsetPart = parts.find(p => p.type === 'timeZoneName');
            
            if (offsetPart && offsetPart.value) {
                // offsetPart.value will be like "GMT+1", "GMT+02:00", "GMT+1:00", etc.
                // Extract the offset part
                const offsetMatch = offsetPart.value.match(/GMT([+-])(\d{1,2})(:?(\d{2}))?/);
                if (offsetMatch) {
                    const sign = offsetMatch[1];
                    const hours = parseInt(offsetMatch[2]) || 0;
                    const minutes = offsetMatch[4] ? parseInt(offsetMatch[4]) : 0;
                    
                    if (minutes === 0) {
                        return 'UTC' + sign + String(hours).padStart(2, '0');
                    } else {
                        return 'UTC' + sign + String(hours).padStart(2, '0') + ':' + String(minutes).padStart(2, '0');
                    }
                }
            }
            
            // Fallback: Calculate offset by comparing what time it is in UTC vs the timezone
            const utcTimeStr = now.toLocaleString('sv-SE', { timeZone: 'UTC' });
            const tzTimeStr = now.toLocaleString('sv-SE', { timeZone: ianaId });
            
            const utcDate = new Date(utcTimeStr.replace(' ', 'T') + 'Z');
            const tzDate = new Date(tzTimeStr.replace(' ', 'T') + 'Z');
            
            const diffMs = tzDate.getTime() - utcDate.getTime();
            const diffHours = diffMs / (1000 * 60 * 60);
            
            const sign = diffHours >= 0 ? '+' : '-';
            const absHours = Math.abs(diffHours);
            const hours = Math.floor(absHours);
            const minutes = Math.round((absHours - hours) * 60);
            
            if (minutes === 0) {
                return 'UTC' + sign + String(hours).padStart(2, '0');
            } else {
                return 'UTC' + sign + String(hours).padStart(2, '0') + ':' + String(minutes).padStart(2, '0');
            }
        } catch (e) {
            console.warn('Could not get timezone offset for', ianaId, ':', e);
            return 'UTC+0';
        }
    }

    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTimezoneChecker);
    } else {
        initTimezoneChecker();
    }

    // Build timezone list dynamically from the browser's supported IANA IDs
    function getSupportedTimezoneIds() {
        try {
            if (typeof Intl.supportedValuesOf === 'function') {
                const values = Intl.supportedValuesOf('timeZone');
                if (values && values.length > 0) return values;
            }
        } catch (e) {
            console.warn('Intl.supportedValuesOf not available, using fallback list', e);
        }
        return ['UTC', 'America/New_York', 'Europe/London', 'Asia/Tokyo', 'Australia/Sydney'];
    }

    function formatTimezoneName(id) {
        try {
            const parts = id.split('/');
            const city = parts[parts.length - 1] || id;
            return city.replace(/_/g, ' ');
        } catch (e) {
            return id;
        }
    }

    function deriveRegion(id) {
        try {
            const parts = id.split('/');
            return parts.length > 1 ? parts[0].replace(/_/g, ' ') : 'Other';
        } catch (e) {
            return 'Other';
        }
    }

    function buildTimezoneList() {
        const ids = getSupportedTimezoneIds();
        return ids.map(id => ({
            id,
            name: formatTimezoneName(id),
            region: deriveRegion(id),
            offset: getCurrentTimezoneOffset(id)
        }));
    }

    const TIMEZONE_OPTIONS = buildTimezoneList();
    // Expose for other inline scripts (profile page, calendar overlays)
    window.TIMEZONE_OPTIONS = TIMEZONE_OPTIONS;

    function initTimezoneChecker() {
        console.log('[Timezone Checker] Initializing...');
        
        // Check if user is logged in (has profile data)
        const userProfileData = document.getElementById('userProfileData');
        if (!userProfileData) {
            // No user profile data found - skipping check
            return; // Not logged in or no profile data
        }

        const profileData = JSON.parse(userProfileData.textContent);
        const savedDetectedTimezone = profileData.detected_timezone || '';
        const selectedTimezone = profileData.selected_timezone || '';
        const confirmedMismatch = profileData.confirmed_timezone_mismatch === true;
        
        console.log('DB detected_timezone:', savedDetectedTimezone);
        console.log('DB Selected timezone:', selectedTimezone);
        console.log('DB confirmed_mismatch:', confirmedMismatch);

        // Detect browser's current timezone
        let browserDetectedTimezone;
        try {
            browserDetectedTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
            
            // For testing: Check sessionStorage first (set by test button), then window.TEST_TIMEZONE (set by console)
            const testTimezone = sessionStorage.getItem('TEST_TIMEZONE') || window.TEST_TIMEZONE;
            if (testTimezone) {
                console.log('⚠️ TEST MODE: Using test timezone:', testTimezone);
                browserDetectedTimezone = testTimezone;
            }
        } catch (e) {
            console.error('Could not detect timezone:', e);
            return;
        }

        // Step 0: Check for first time login - empty selected_timezone means first login
        if (!selectedTimezone || selectedTimezone.trim() === '') {
            // Update detected_timezone first
            if (browserDetectedTimezone !== savedDetectedTimezone) {
                updateDetectedTimezone(browserDetectedTimezone, function(updatedData) {
                    showFirstTimeLoginModal(updatedData.detected_timezone);
                });
            } else {
                showFirstTimeLoginModal(browserDetectedTimezone);
            }
            return;
        }

        // Step 1: Update detected_timezone if browser detected timezone is different
        // This auto-updates - user only decides if there's a mismatch with selected_timezone
        if (browserDetectedTimezone !== savedDetectedTimezone) {
            updateDetectedTimezone(browserDetectedTimezone, function(updatedData) {
                // After updating detected timezone, check for mismatch with selected
                checkTimezoneMismatch(updatedData.detected_timezone, updatedData.selected_timezone, updatedData.confirmed_mismatch);
            });
        } else {
            // Step 2: Check for mismatch with current data
            checkTimezoneMismatch(browserDetectedTimezone, selectedTimezone, confirmedMismatch);
        }
    }

    function updateDetectedTimezone(detectedTimezone, callback) {
        fetch('/dashboard/update-timezone/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                action: 'update_detected',
                detected_timezone: detectedTimezone
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('✓ Detected timezone updated:', detectedTimezone);
                // Update the userProfileData element
                const userProfileData = document.getElementById('userProfileData');
                if (userProfileData) {
                    const profileData = JSON.parse(userProfileData.textContent);
                    profileData.detected_timezone = data.detected_timezone;
                    profileData.selected_timezone = data.selected_timezone;
                    profileData.confirmed_timezone_mismatch = data.confirmed_mismatch;
                    userProfileData.textContent = JSON.stringify(profileData);
                }
                if (callback) {
                    callback({
                        detected_timezone: data.detected_timezone,
                        selected_timezone: data.selected_timezone,
                        confirmed_mismatch: data.confirmed_mismatch
                    });
                }
            } else {
                console.error('[Timezone Checker] Failed to update detected timezone:', data.error);
                if (callback) {
                    callback({
                        detected_timezone: detectedTimezone,
                        selected_timezone: '',
                        confirmed_mismatch: false
                    });
                }
            }
        })
        .catch(error => {
            console.error('[Timezone Checker] Error updating detected timezone:', error);
            if (callback) {
                callback({
                    detected_timezone: detectedTimezone,
                    selected_timezone: '',
                    confirmed_mismatch: false
                });
            }
        });
    }

    function checkTimezoneMismatch(detectedTimezone, selectedTimezone, confirmedMismatch) {
        // Note: detected_timezone is already updated in DB at this point (auto-updated)
        
        // If no selected timezone, set it to detected and we're done
        if (!selectedTimezone || selectedTimezone.trim() === '') {
            updateSelectedTimezone(detectedTimezone, false, function() {
                // All good
            });
            return;
        }

        // Check if selected and detected match
        if (selectedTimezone === detectedTimezone) {
            // If confirmed_mismatch is True, set it to False (they match now)
            if (confirmedMismatch) {
                updateSelectedTimezone(selectedTimezone, false, function() {
                    // Confirmed mismatch cleared
                });
            }
            return; // No mismatch, exit
        }

        // There's a mismatch between detected and selected
        // Check if user has already confirmed the mismatch
        if (confirmedMismatch) {
            return; // User already confirmed, don't show popup
        }

        // Show popup asking user to confirm which timezone to use
        showTimezoneMismatchModal(detectedTimezone, selectedTimezone);
    }

    function showFirstTimeLoginModal(detectedTz) {
        // Create modal overlay
        const modalOverlay = document.createElement('div');
        modalOverlay.className = 'timezone-modal-overlay';
        modalOverlay.id = 'timezoneModalOverlay';
        
        // Create modal content
        const modalContent = document.createElement('div');
        modalContent.className = 'timezone-modal-content';
        
        let detectedTzName = detectedTz;
        const detectedTzObj = TIMEZONE_OPTIONS.find(tz => tz.id === detectedTz);
        if (detectedTzObj) {
            const currentOffset = getCurrentTimezoneOffset(detectedTz);
            detectedTzName = detectedTzObj.name + ' (' + currentOffset + ')';
        }
        
        // Format current time in detected timezone
        const now = new Date();
        const detectedTime = formatTime(now, detectedTz);
        const detectedDate = formatDate(now, detectedTz);
        
        modalContent.innerHTML = `
            <div class="timezone-modal-header">
                <h3 class="timezone-modal-title">
                    <i class="fas fa-clock" style="color: var(--dash-primary); margin-right: 8px;"></i>
                    Set Your Timezone
                </h3>
                <button type="button" class="timezone-modal-close" id="timezoneModalClose">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="timezone-modal-body">
                <p class="timezone-modal-text">
                    To ensure accurate session scheduling, please set your timezone. We've detected your location timezone, but you can choose a different one if needed.
                </p>
                <div class="timezone-mismatch-comparison">
                    <div class="timezone-mismatch-item timezone-detected">
                        <div class="timezone-mismatch-label">Detected (Current Location)</div>
                        <div class="timezone-mismatch-value">${detectedTzName}</div>
                        <div class="timezone-mismatch-date">${detectedDate}</div>
                        <div class="timezone-mismatch-time">${detectedTime}</div>
                        <button type="button" class="btn btn-primary btn-timezone-action" id="useDetectedBtn">
                            Use detected timezone
                        </button>
                    </div>
                    <div class="timezone-mismatch-divider">or</div>
                    <div class="timezone-mismatch-item timezone-selected">
                        <div class="timezone-mismatch-label">Select Your Timezone</div>
                        <div class="timezone-mismatch-select-wrapper">
                            <div class="autocomplete-container" style="position: relative;">
                                <input type="text" id="timezoneModalInput" class="form-input autocomplete-input" placeholder="Search for your timezone..." autocomplete="off" value="">
                                <input type="hidden" id="timezoneModalValue" value="">
                                <div class="autocomplete-suggestions" id="timezoneModalSuggestions"></div>
                            </div>
                        </div>
                        <div class="timezone-mismatch-date" id="timezoneModalSelectedDate" style="display: none;"></div>
                        <div class="timezone-mismatch-time" id="timezoneModalSelectedTime" style="display: none;"></div>
                        <button type="button" class="btn btn-outline btn-timezone-action" id="useSelectedBtn" disabled>
                            Select a timezone first
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        modalOverlay.appendChild(modalContent);
        document.body.appendChild(modalOverlay);
        
        // Show modal with animation
        setTimeout(() => {
            modalOverlay.classList.add('active');
        }, 100);
        
        // Get elements
        const closeBtn = document.getElementById('timezoneModalClose');
        const useDetectedBtn = document.getElementById('useDetectedBtn');
        const useSelectedBtn = document.getElementById('useSelectedBtn');
        const timezoneInput = document.getElementById('timezoneModalInput');
        const timezoneValue = document.getElementById('timezoneModalValue');
        const timezoneSuggestions = document.getElementById('timezoneModalSuggestions');
        const selectedDateEl = document.getElementById('timezoneModalSelectedDate');
        const selectedTimeEl = document.getElementById('timezoneModalSelectedTime');
        
        // Track selected timezone for button text
        let currentSelectedTz = null;
        
        // Initialize timezone autocomplete
        initializeTimezoneAutocomplete(timezoneInput, timezoneValue, timezoneSuggestions, TIMEZONE_OPTIONS, function(selectedTzObj) {
            currentSelectedTz = selectedTzObj.id;
            
            // Update button text
            useSelectedBtn.textContent = `Set timezone to ${selectedTzObj.name} (${selectedTzObj.offset})`;
            useSelectedBtn.disabled = false;
            
            // Update displayed time
            const now = new Date();
            const newSelectedTime = formatTime(now, selectedTzObj.id);
            const newSelectedDate = formatDate(now, selectedTzObj.id);
            if (selectedDateEl) {
                selectedDateEl.textContent = newSelectedDate;
                selectedDateEl.style.display = 'block';
            }
            if (selectedTimeEl) {
                selectedTimeEl.textContent = newSelectedTime;
                selectedTimeEl.style.display = 'block';
            }
        });
        
        // Close button and overlay click - select detected timezone
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                updateToDetectedTimezone(detectedTz, true); // true = close immediately
            });
        }
        
        // Close on overlay click - select detected timezone
        modalOverlay.addEventListener('click', function(e) {
            if (e.target === modalOverlay) {
                updateToDetectedTimezone(detectedTz, true); // true = close immediately
            }
        });
        
        if (useDetectedBtn) {
            useDetectedBtn.addEventListener('click', function() {
                updateToDetectedTimezone(detectedTz, true); // true = close immediately
            });
        }
        
        if (useSelectedBtn) {
            useSelectedBtn.addEventListener('click', function() {
                if (currentSelectedTz) {
                    updateSelectedTimezone(currentSelectedTz, false, function() {
                        closeModal();
                        window.location.reload();
                    });
                }
            });
        }
        
        function closeModal() {
            modalOverlay.classList.remove('active');
            setTimeout(() => {
                if (modalOverlay.parentNode) {
                    document.body.removeChild(modalOverlay);
                }
            }, 300);
        }
    }

    function showTimezoneMismatchModal(detectedTz, selectedTz) {
        // Create modal overlay
        const modalOverlay = document.createElement('div');
        modalOverlay.className = 'timezone-modal-overlay';
        modalOverlay.id = 'timezoneModalOverlay';
        
        // Create modal content
        const modalContent = document.createElement('div');
        modalContent.className = 'timezone-modal-content';
        
        let detectedTzName = detectedTz;
        let selectedTzName = selectedTz;
        
        const detectedTzObj = TIMEZONE_OPTIONS.find(tz => tz.id === detectedTz);
        const selectedTzObj = TIMEZONE_OPTIONS.find(tz => tz.id === selectedTz);
        
        if (detectedTzObj) {
            // Use dynamic offset calculation (handles DST)
            const currentOffset = getCurrentTimezoneOffset(detectedTz);
            detectedTzName = detectedTzObj.name + ' (' + currentOffset + ')';
        }
        if (selectedTzObj) {
            // Use dynamic offset calculation (handles DST)
            const currentOffset = getCurrentTimezoneOffset(selectedTz);
            selectedTzName = selectedTzObj.name + ' (' + currentOffset + ')';
        }
        
        // Format current time in both timezones
        const now = new Date();
        const detectedTime = formatTime(now, detectedTz);
        const detectedDate = formatDate(now, detectedTz);
        const selectedTime = formatTime(now, selectedTz);
        const selectedDate = formatDate(now, selectedTz);
        
        // Build timezone options HTML
        let timezoneOptionsHTML = '';
        TIMEZONE_OPTIONS.forEach(tz => {
            const selected = tz.id === selectedTz ? 'selected' : '';
            // Use dynamic offset calculation (handles DST)
            const currentOffset = getCurrentTimezoneOffset(tz.id);
            timezoneOptionsHTML += `<option value="${tz.id}" ${selected}>${tz.name} (${currentOffset})</option>`;
        });
        
        modalContent.innerHTML = `
            <div class="timezone-modal-header">
                <h3 class="timezone-modal-title">
                    <i class="fas fa-clock" style="color: var(--dash-primary); margin-right: 8px;"></i>
                    Timezone Mismatch Detected
                </h3>
                <button type="button" class="timezone-modal-close" id="timezoneModalClose">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="timezone-modal-body">
                <p class="timezone-modal-text">
                    We detected that your current location timezone doesn't match your selected timezone.
                </p>
                <div class="timezone-mismatch-comparison">
                    <div class="timezone-mismatch-item timezone-detected">
                        <div class="timezone-mismatch-label">Detected (Current Location)</div>
                        <div class="timezone-mismatch-value">${detectedTzName}</div>
                        <div class="timezone-mismatch-date">${detectedDate}</div>
                        <div class="timezone-mismatch-time">${detectedTime}</div>
                        <button type="button" class="btn btn-primary btn-timezone-action" id="useDetectedBtn">
                            Detected timezone is correct
                        </button>
                    </div>
                    <div class="timezone-mismatch-divider">or</div>
                    <div class="timezone-mismatch-item timezone-selected">
                        <div class="timezone-mismatch-label">Your Selected Timezone</div>
                        <div class="timezone-mismatch-select-wrapper">
                            <div class="autocomplete-container" style="position: relative;">
                                <input type="text" id="timezoneModalInput" class="form-input autocomplete-input" placeholder="Search for your timezone..." autocomplete="off" value="${selectedTzName}">
                                <input type="hidden" id="timezoneModalValue" value="${selectedTz}">
                                <div class="autocomplete-suggestions" id="timezoneModalSuggestions"></div>
                            </div>
                        </div>
                        <div class="timezone-mismatch-date" id="timezoneModalSelectedDate">${selectedDate}</div>
                        <div class="timezone-mismatch-time" id="timezoneModalSelectedTime">${selectedTime}</div>
                        <button type="button" class="btn btn-outline btn-timezone-action" id="useSelectedBtn">
                            Don't change my timezone
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        modalOverlay.appendChild(modalContent);
        document.body.appendChild(modalOverlay);
        
        // Show modal with animation
        setTimeout(() => {
            modalOverlay.classList.add('active');
        }, 100);
        
        // Get elements
        const closeBtn = document.getElementById('timezoneModalClose');
        const useDetectedBtn = document.getElementById('useDetectedBtn');
        const useSelectedBtn = document.getElementById('useSelectedBtn');
        const timezoneInput = document.getElementById('timezoneModalInput');
        const timezoneValue = document.getElementById('timezoneModalValue');
        const timezoneSuggestions = document.getElementById('timezoneModalSuggestions');
        const selectedDateEl = document.getElementById('timezoneModalSelectedDate');
        const selectedTimeEl = document.getElementById('timezoneModalSelectedTime');
        
        // Track selected timezone for button text
        let currentSelectedTz = selectedTz;
        const originalSelectedTz = selectedTz;
        
        // Initialize timezone autocomplete
        initializeTimezoneAutocomplete(timezoneInput, timezoneValue, timezoneSuggestions, TIMEZONE_OPTIONS, function(selectedTzObj) {
            currentSelectedTz = selectedTzObj.id;
            
            // Update button text - use dynamic offset (handles DST)
            if (selectedTzObj.id === originalSelectedTz) {
                useSelectedBtn.textContent = "Don't change my timezone";
            } else {
                const currentOffset = getCurrentTimezoneOffset(selectedTzObj.id);
                useSelectedBtn.textContent = `Change my timezone to ${selectedTzObj.name} (${currentOffset})`;
            }
            
            // Update displayed time
            const now = new Date();
            const newSelectedTime = formatTime(now, selectedTzObj.id);
            const newSelectedDate = formatDate(now, selectedTzObj.id);
            if (selectedDateEl) selectedDateEl.textContent = newSelectedDate;
            if (selectedTimeEl) selectedTimeEl.textContent = newSelectedTime;
        });
        
        // Close button and overlay click - select detected timezone
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                updateToDetectedTimezone(detectedTz, true); // true = close immediately
            });
        }
        
        // Close on overlay click - select detected timezone
        modalOverlay.addEventListener('click', function(e) {
            if (e.target === modalOverlay) {
                updateToDetectedTimezone(detectedTz, true); // true = close immediately
            }
        });
        
        if (useDetectedBtn) {
            useDetectedBtn.addEventListener('click', function() {
                updateToDetectedTimezone(detectedTz, true); // true = close immediately
            });
        }
        
        if (useSelectedBtn) {
            useSelectedBtn.addEventListener('click', function() {
                updateSelectedTimezone(currentSelectedTz, true, function() {
                    closeModal();
                    window.location.reload();
                });
            });
        }
        
        function closeModal() {
            modalOverlay.classList.remove('active');
            setTimeout(() => {
                if (modalOverlay.parentNode) {
                    document.body.removeChild(modalOverlay);
                }
            }, 300);
        }
    }

    function updateToDetectedTimezone(detectedTimezone, closeImmediately) {
        const button = document.getElementById('useDetectedBtn');
        const modalOverlay = document.getElementById('timezoneModalOverlay');
        
        if (button) {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';
        }
        
        // Close modal immediately if requested
        if (closeImmediately && modalOverlay) {
            modalOverlay.classList.remove('active');
            setTimeout(() => {
                if (modalOverlay.parentNode) {
                    document.body.removeChild(modalOverlay);
                }
            }, 300);
        }
        
        fetch('/dashboard/update-timezone/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                action: 'use_detected',
                detected_timezone: detectedTimezone
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('DB detected_timezone:', data.detected_timezone || '');
                console.log('DB Selected timezone:', data.selected_timezone);
                console.log('DB confirmed_mismatch:', data.confirmed_mismatch);
                
                if (button && !closeImmediately) {
                    button.innerHTML = '<i class="fas fa-check"></i> Updated!';
                    button.style.background = 'var(--dash-primary)';
                }
                setTimeout(() => {
                    window.location.reload();
                }, closeImmediately ? 100 : 500);
            } else {
                if (button) {
                    button.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
                    button.style.background = '#ef4444';
                    setTimeout(() => {
                        button.disabled = false;
                        button.innerHTML = 'Detected timezone is correct';
                        button.style.background = '';
                    }, 2000);
                }
            }
        })
        .catch(error => {
            console.error('Error updating to detected timezone:', error);
            if (button) {
                button.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
                button.style.background = '#ef4444';
                setTimeout(() => {
                    button.disabled = false;
                    button.innerHTML = 'Detected timezone is correct';
                    button.style.background = '';
                }, 2000);
            }
        });
    }

    function updateSelectedTimezone(selectedTimezone, confirmedMismatch, callback) {
        fetch('/dashboard/update-timezone/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                action: 'update_selected',
                selected_timezone: selectedTimezone,
                confirmed_mismatch: confirmedMismatch
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('DB detected_timezone:', data.detected_timezone || '');
                console.log('DB Selected timezone:', data.selected_timezone);
                console.log('DB confirmed_mismatch:', data.confirmed_mismatch);
                // Update the userProfileData element
                const userProfileData = document.getElementById('userProfileData');
                if (userProfileData) {
                    const profileData = JSON.parse(userProfileData.textContent);
                    profileData.selected_timezone = data.selected_timezone;
                    profileData.confirmed_timezone_mismatch = data.confirmed_mismatch;
                    userProfileData.textContent = JSON.stringify(profileData);
                }
                if (callback) callback();
            } else {
                console.error('Failed to update selected timezone:', data.error);
                if (callback) callback();
            }
        })
        .catch(error => {
            console.error('Error updating selected timezone:', error);
            if (callback) callback();
        });
    }

    function formatTime(date, timezone) {
        try {
            const formatter = new Intl.DateTimeFormat('en-US', {
                timeZone: timezone,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: true
            });
            return formatter.format(date);
        } catch (e) {
            return 'Unable to format time';
        }
    }

    function formatDate(date, timezone) {
        try {
            const formatter = new Intl.DateTimeFormat('en-US', {
                timeZone: timezone,
                weekday: 'short',
                month: 'short',
                day: 'numeric'
            });
            return formatter.format(date);
        } catch (e) {
            return 'Unable to format date';
        }
    }

    function initializeTimezoneAutocomplete(input, hiddenInput, suggestionsEl, timezones, onSelect) {
        if (!input || !suggestionsEl || !timezones || timezones.length === 0) {
            console.error('[Timezone Autocomplete] Missing required elements or timezones data');
            return;
        }
        
        let selectedTimezone = null;
        
        // Find current timezone if set
        if (hiddenInput && hiddenInput.value) {
            const currentTz = timezones.find(tz => tz.id === hiddenInput.value);
            if (currentTz) {
                selectedTimezone = currentTz;
                input.value = currentTz.name + ' (' + (currentTz.offset || '') + ')';
            }
        }
        
        function filterTimezoneSuggestions(query) {
            if (!query || query.trim() === '') {
                return timezones; // Show all if empty
            }
            const lowerQuery = query.toLowerCase();
            return timezones.filter(tz => 
                (tz.name && tz.name.toLowerCase().includes(lowerQuery)) ||
                (tz.region && tz.region.toLowerCase().includes(lowerQuery)) ||
                (tz.id && tz.id.toLowerCase().includes(lowerQuery)) ||
                (tz.offset && tz.offset.toLowerCase().includes(lowerQuery))
            );
        }
        
        function displayTimezoneSuggestions(suggestions) {
            if (!suggestionsEl) return;
            
            if (suggestions.length === 0) {
                suggestionsEl.style.display = 'none';
                return;
            }
            
            // Group by region
            const grouped = {};
            suggestions.forEach(tz => {
                const region = (tz.region || 'Other');
                if (!grouped[region]) {
                    grouped[region] = [];
                }
                grouped[region].push(tz);
            });
            
            suggestionsEl.innerHTML = '';
            
            Object.keys(grouped).sort().forEach(region => {
                const regionHeader = document.createElement('div');
                regionHeader.className = 'timezone-region-header';
                regionHeader.textContent = region;
                suggestionsEl.appendChild(regionHeader);
                
                grouped[region].forEach(tz => {
                    const item = document.createElement('div');
                    item.className = 'suggestion-item timezone-item';
                    item.style.cursor = 'pointer';
                    item.innerHTML = `
                        <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                            <div>
                                <div style="font-weight: 500; color: var(--dash-text-main);">${tz.name || tz.id}</div>
                                <div style="font-size: 0.85rem; color: var(--dash-text-muted);">${tz.id}</div>
                            </div>
                            <div style="font-size: 0.85rem; color: var(--dash-text-muted);">${tz.offset || ''}</div>
                        </div>
                    `;
                    item.addEventListener('click', function(e) {
                        e.stopPropagation();
                        selectedTimezone = tz;
                        input.value = (tz.name || tz.id) + ' (' + (tz.offset || '') + ')';
                        if (hiddenInput) hiddenInput.value = tz.id;
                        suggestionsEl.style.display = 'none';
                        if (onSelect) onSelect(tz);
                    });
                    suggestionsEl.appendChild(item);
                });
            });
            
            suggestionsEl.style.display = 'block';
            suggestionsEl.style.maxHeight = '400px';
            suggestionsEl.style.overflowY = 'auto';
            suggestionsEl.style.zIndex = '10001'; // Above modal
        }
        
        let timezoneDebounceTimer;
        
        // Show suggestions on focus
        input.addEventListener('focus', function() {
            const query = this.value.trim();
            displayTimezoneSuggestions(filterTimezoneSuggestions(query));
        });
        
        // Show suggestions as user types
        input.addEventListener('input', function() {
            clearTimeout(timezoneDebounceTimer);
            const query = this.value.trim();
            timezoneDebounceTimer = setTimeout(() => {
                displayTimezoneSuggestions(filterTimezoneSuggestions(query));
            }, 150); // Reduced debounce for better responsiveness
        });
        
        // Close suggestions when clicking outside (but not on modal overlay)
        const clickHandler = function(event) {
            if (input && suggestionsEl && 
                !input.contains(event.target) && 
                !suggestionsEl.contains(event.target)) {
                suggestionsEl.style.display = 'none';
            }
        };
        
        // Use capture phase to handle clicks properly
        document.addEventListener('click', clickHandler, true);
        
        // Store cleanup function on input element for later removal
        input._timezoneAutocompleteCleanup = function() {
            document.removeEventListener('click', clickHandler, true);
        };
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
})();
