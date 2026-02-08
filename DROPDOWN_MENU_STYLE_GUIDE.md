# Dropdown Menu Style Guide

This document describes the standard styling and structure for dropdown menus in the Healthy Mentoring application. Use this as a reference when creating new dropdown menus to ensure consistency across the application.

## Overview

This guide covers dropdown menus in three main scenarios:
1. **Form Input Dropdowns** - Custom styled select inputs for forms (e.g., Mentor Type selector)
2. **Navigation/Action Dropdowns** - Dropdown menus triggered by clicking any element (e.g., user profile menu, notification menu)
3. **Row-Action Dropdowns** - Three-dots (ellipsis) menus inside scrollable lists (e.g. upcoming sessions, project stages). These use fixed positioning so the menu is never clipped by overflow and repositions when the user scrolls.

All dropdown menus should follow the styling patterns established in the navbar avatar dropdown menu. This guide covers font styling, hover effects, rounded corners, icon styling, spacing, and trigger element styling.

---

## Row-Action Dropdowns (Scrollable Lists)

Use this pattern when the dropdown lives inside a **scrollable container** (e.g. a list of sessions, stages, or cards). The menu must stay visible when the user scrolls and must not be clipped by the parent’s `overflow`.

### When to use
- Upcoming sessions list (three-dots per row)
- Project stages list (three-dots per stage)
- Any list or timeline where each row has an actions menu and the list can scroll

### HTML structure (required)

Use this **exact** structure so the base template’s JavaScript can handle opening, fixed positioning, and scroll repositioning:

```html
<div class="dropdown">
  <button class="session-action-btn" type="button" onclick="toggleDropdown(this)">
    <i class="fas fa-ellipsis-h"></i>
  </button>
  <div class="dropdown-menu" onclick="event.stopPropagation();">
    <button type="button" class="dropdown-item first-item" onclick="doAction1(); event.stopPropagation();">
      <i class="fas fa-edit"></i>
      <span>Edit</span>
    </button>
    <button type="button" class="dropdown-item delete-item last-item" onclick="doAction2(); event.stopPropagation();">
      <i class="fas fa-trash"></i>
      <span>Delete</span>
    </button>
  </div>
</div>
```

**Required:**
- **Wrapper:** One element with class `dropdown` (no custom container class).
- **Trigger:** A **button** with class `session-action-btn` and `onclick="toggleDropdown(this)"`. The trigger must be the **direct previous sibling** of the menu (base uses `button.nextElementSibling` to find the menu).
- **Menu:** A **div** with class `dropdown-menu`. It receives `show` and `session-row-dropdown-menu--fixed` when open. Use `onclick="event.stopPropagation();"` on the menu so clicks on items don’t close it before the handler runs.
- **Items:** Buttons (or links) with class `dropdown-item`. Add `first-item` to the first and `last-item` to the last for rounded corners. Use `event.stopPropagation()` in item `onclick` if needed.

**Optional:** Add an extra class on the menu for scoped styling (e.g. `dropdown-menu stage-actions-menu`), then style only items inside that menu (e.g. red delete hover, custom padding).

### Scroll context (where the dropdown lives)

The base template (`dashboard_mentor/base.html`) applies **fixed positioning and scroll repositioning** only when the dropdown is inside a known scroll context:

- **`.session-timeline-container`** – e.g. upcoming sessions, session history.
- **`#stagesList`** – project detail stages list.

If you add a **new** scrollable list that should have row-action dropdowns:

1. Keep the same HTML structure above (`dropdown`, `session-action-btn`, `dropdown-menu`).
2. In `base.html`, extend the condition that decides “use fixed positioning” to include your container. In `toggleDropdown`, the check is `dropdown.closest('.session-timeline-container') || dropdown.closest('#stagesList')`. Add your container (e.g. `dropdown.closest('#myListId')`).
3. In `positionSessionDropdownFixed`, set `scrollContainer` the same way (e.g. `dropdown.closest('.session-timeline-container') || dropdown.closest('#stagesList') || dropdown.closest('#myListId')`).
4. If your list scrolls via a **specific** element (e.g. `#dashboardMain` or a div with `overflow-y: auto`), the base logic already attaches scroll listeners to `window` and, for `#stagesList`, to all scrollable ancestors of the trigger. For a new context you may need to add the same “scrollable ancestors” behaviour for your container in `positionSessionDropdownFixed` (see the `scrollContainer.id === 'stagesList'` branch).

### JavaScript: use the global toggle only

- **Do not** implement a custom open/close or positioning function for this pattern.
- **Do** use the global `toggleDropdown(button)` provided by the mentor base template. It:
  - Opens the menu and applies fixed positioning when the dropdown is inside a recognized scroll context.
  - Repositions the menu on scroll so it stays under the trigger.
  - Closes other open `.dropdown-menu` and closes on outside click (any click not inside a `.dropdown`).

When an item’s action should close the menu (e.g. “Edit” opens a modal), close it explicitly:

```javascript
// Example: close the row’s dropdown before opening a modal
const rowActions = document.getElementById('rowActions_' + rowId);
if (rowActions) {
  const menu = rowActions.querySelector('.dropdown-menu.show');
  if (menu) {
    menu.classList.remove('show');
    if (typeof clearSessionDropdownFixed === 'function') clearSessionDropdownFixed(menu);
  }
}
```

### CSS: base and optional scoped styles

- **Base styles** are in `static/css/dashboard.css`:
  - `.dropdown`, `.dropdown-menu`, `.dropdown-menu.show`, `.dropdown-menu.session-row-dropdown-menu--fixed`
  - `.session-action-btn` (no border, circular, used as the three-dots trigger)
- **Position** when fixed is set by the base script (below the trigger, right-aligned; flips above if no room). Do not override `position`/`top`/`left` for the open state.
- **Optional:** Add a class on the menu (e.g. `stage-actions-menu`) and scope item styles (padding, icons, first/last rounded corners, red hover for delete) under that class so they don’t affect other dropdowns.

Example for a “delete” item and rounded corners (same idea as stage-actions):

```css
.your-menu-class .dropdown-item.first-item { border-radius: 12px 12px 0 0; }
.your-menu-class .dropdown-item.last-item { border-radius: 0 0 12px 12px; }
.your-menu-class .dropdown-item.delete-item:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}
.your-menu-class .dropdown-item.delete-item:hover i { color: #ef4444; }
```

### Keeping the trigger visible while the menu is open

If the trigger (or its wrapper) is hidden by default and only shown on row hover (e.g. `opacity: 0` until `.stage-row:hover`), it will disappear when the user moves the mouse to the menu. Keep it visible while the menu is open by using `:has(.dropdown-menu.show)`:

```css
.stage-row:hover .row-actions,
.stage-row .row-actions:has(.dropdown-menu.show) {
  opacity: 1;
}
```

Apply the same idea to whatever wrapper you use so the three-dots (and the open menu) stay visible until the user closes the menu.

### Checklist for row-action dropdowns

- [ ] Wrapper is `<div class="dropdown">` with no extra container around trigger + menu.
- [ ] Trigger is a **button** with class `session-action-btn` and `onclick="toggleDropdown(this)"`.
- [ ] Menu is the **immediate next sibling** of the trigger and has class `dropdown-menu`.
- [ ] Dropdown is inside a recognized scroll context (e.g. `.session-timeline-container` or `#stagesList`), or the base template was updated to support your container.
- [ ] Menu has `onclick="event.stopPropagation();"` so item clicks don’t bubble and close the menu before handlers run.
- [ ] Item actions that should close the menu call `clearSessionDropdownFixed(menu)` (from base) when closing.
- [ ] If the trigger is only visible on row hover, CSS keeps it visible with `:has(.dropdown-menu.show)` so the menu stays usable.

---

## HTML Structure

### Form Input Dropdown Structure

For form inputs (custom select elements):

```html
<div class="custom-dropdown-container">
  <button type="button" class="custom-dropdown-trigger" id="dropdownTrigger">
    <span class="dropdown-selected-text" id="selectedText">Select an option</span>
    <i class="fas fa-chevron-down"></i>
  </button>
  <input type="hidden" name="field_name" id="hiddenInput" value="">
  <div class="custom-dropdown-menu" id="dropdownMenu">
    <button type="button" class="dropdown-item first-item" data-value="value1">
      <span>Option 1</span>
    </button>
    <button type="button" class="dropdown-item" data-value="value2">
      <span>Option 2</span>
    </button>
    <button type="button" class="dropdown-item last-item" data-value="value3">
      <span>Option 3</span>
    </button>
  </div>
</div>
```

### Navigation/Action Dropdown Structure

For navigation menus or action menus triggered by any element:

```html
<div class="dropdown-container">
  <!-- Trigger can be any element: button, div, link, etc. -->
  <button class="dropdown-trigger" id="dropdownTrigger">
    <!-- Trigger content -->
    <span>Click me</span>
    <i class="fas fa-chevron-down"></i>
  </button>
  <div class="dropdown-menu" id="dropdownMenu">
    <a href="#" class="dropdown-item first-item">
      <i class="fas fa-icon-name"></i>
      <span>Item Text</span>
    </a>
    <a href="#" class="dropdown-item">
      <i class="fas fa-icon-name"></i>
      <span>Item Text</span>
    </a>
    <!-- Divider (if needed) -->
    <div class="dropdown-divider"></div>
    <!-- Last item (usually logout) -->
    <form action="{% url 'url_name' %}" method="post" class="dropdown-item-form">
      {% csrf_token %}
      <button type="submit" class="dropdown-item logout-item last-item">
        <i class="fas fa-icon-name"></i>
        <span>Item Text</span>
      </button>
    </form>
  </div>
</div>
```

### Key Classes

- **Container**: `.dropdown-container`, `.custom-dropdown-container`, `.user-profile-dropdown` (or custom name)
- **Trigger**: `.dropdown-trigger`, `.custom-dropdown-trigger` (or custom name)
- **Menu**: `.dropdown-menu`, `.custom-dropdown-menu` (or custom name)
- **Items**: `.dropdown-item`
- **First Item**: Add `.first-item` class (for rounded top corners)
- **Last Item**: Add `.last-item` class (for rounded bottom corners)
- **Divider**: `.dropdown-divider`
- **Form Items**: `.dropdown-item-form` (for forms like logout)

---

## CSS Styling

### Dropdown Menu Container

```css
.dropdown-menu,
.custom-dropdown-menu {
  position: absolute;
  top: calc(100% + 8px);  /* 8px gap from trigger */
  right: 0;  /* or left: 0 for left-aligned */
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
  min-width: 200px;
  padding: 0;  /* ⚠️ IMPORTANT: No padding on container */
  opacity: 0;
  visibility: hidden;
  transform: translateY(-10px);
  transition: all 0.2s ease;
  z-index: 10005;  /* ⚠️ IMPORTANT: High z-index to appear above modals, footers, and other UI elements */
}

.dropdown-container.active .dropdown-menu,
.custom-dropdown-container.active .custom-dropdown-menu {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}
```

**⚠️ CRITICAL NOTE ON PADDING:**
- **DO NOT** add padding to `.dropdown-menu` container
- Padding is applied individually to each `.dropdown-item` (12px 20px)
- This ensures proper rounded corner behavior on hover

---

### Dropdown Trigger Styling

#### Form Input Trigger (Custom Select)

```css
.custom-dropdown-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 10px 16px;
  background: white;
  border: 1px solid var(--dash-border);
  border-radius: 8px;
  color: var(--dash-text-main);
  font-size: 0.95rem;
  font-weight: 400;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.custom-dropdown-trigger:hover {
  /* ⚠️ DO NOT add background color on hover */
}

.custom-dropdown-trigger i {
  color: var(--dash-text-light);
  font-size: 0.85rem;
  transition: transform 0.2s ease;
}

.custom-dropdown-container.active .custom-dropdown-trigger i {
  transform: rotate(180deg);
}
```

**Key Points:**
- Form input triggers should **NOT** have background color changes on hover
- Only border color should change on hover (to green)
- Chevron icon rotates 180° when dropdown is active
- Background remains white at all times

#### Navigation/Action Trigger

For non-form dropdowns, the trigger can have different styling based on context:

```css
.dropdown-trigger {
  /* Style as needed for your use case */
  /* Can have background color changes, etc. */
  /* This is flexible based on design requirements */
}
```

---

### Dropdown Item Styling

#### Base Item Styles

```css
.dropdown-item {
  display: flex;
  align-items: center;
  gap: 12px;  /* Space between icon and text */
  padding: 12px 20px;  /* Vertical: 12px, Horizontal: 20px */
  color: var(--dash-text-main);  /* #1e293b */
  text-decoration: none;
  transition: background 0.2s ease;
  border: none;
  background: transparent;
  width: 100%;
  cursor: pointer;
  font-size: 0.95rem;  /* ~15.2px */
  font-weight: 400;  /* Normal weight */
  text-align: left;
}
```

#### Font Styling

- **Font Size**: `0.95rem` (~15.2px)
- **Font Weight**: `400` (normal)
- **Font Family**: Inherits from body (typically system fonts)
- **Color**: `var(--dash-text-main)` which is `#1e293b`
- **Text Decoration**: `none`

#### Hover State

**⚠️ IMPORTANT: Hover colors differ based on dropdown type**

**For Navigation/Action Dropdowns:**
```css
.dropdown-item:hover {
  background: rgba(16, 185, 129, 0.1);  /* Light green background */
  color: var(--dash-primary);  /* #10b981 - green text */
}
```

**For Form Input Dropdowns (e.g., client selection, template selection):**
```css
.dropdown-item:hover {
  background: #f1f5f9;  /* Light grey background */
  color: #1e293b;  /* Dark text */
}
```

**Note:** Form dropdowns should use light grey hover to differentiate from action/navigation dropdowns which use green.

---

### Rounded Corners on Hover

**⚠️ IMPORTANT: Corner rounding depends on the number of items**

#### Single Item (1 option)

When there is only **one option** in the dropdown:

```css
.dropdown-item:only-child {
  border-radius: 12px;  /* All corners rounded */
}

.dropdown-item:only-child:hover {
  border-radius: 12px;  /* Maintain all rounded corners on hover */
}
```

**Result:** All four corners are rounded (`12px`).

---

#### Two Items (2 options)

When there are **exactly two options**:

```css
/* First item - top corners rounded */
.dropdown-item.first-item:first-child,
.dropdown-item:first-child:not(:last-child) {
  border-radius: 12px 12px 0 0;  /* Top-left, top-right rounded */
}

.dropdown-item.first-item:first-child:hover,
.dropdown-item:first-child:not(:last-child):hover {
  border-radius: 12px 12px 0 0;  /* Maintain rounded top corners on hover */
}

/* Last item - bottom corners rounded */
.dropdown-item.last-item:last-child,
.dropdown-item:last-child:not(:first-child) {
  border-radius: 0 0 12px 12px;  /* Bottom-left, bottom-right rounded */
}

.dropdown-item.last-item:last-child:hover,
.dropdown-item:last-child:not(:first-child):hover {
  border-radius: 0 0 12px 12px;  /* Maintain rounded bottom corners on hover */
}
```

**Result:**
- First item: Top corners rounded (`12px 12px 0 0`), bottom corners NOT rounded
- Second item: Top corners NOT rounded, bottom corners rounded (`0 0 12px 12px`)

---

#### Three or More Items (3+ options)

When there are **three or more options**:

```css
/* First item - top corners rounded */
.dropdown-item.first-item,
.dropdown-item:first-child {
  border-radius: 12px 12px 0 0;  /* Top-left, top-right rounded */
}

.dropdown-item.first-item:hover,
.dropdown-item:first-child:hover {
  border-radius: 12px 12px 0 0;  /* Maintain rounded top corners on hover */
}

/* Middle items - NO rounded corners */
.dropdown-item:not(:first-child):not(:last-child) {
  border-radius: 0;  /* No rounded corners */
}

.dropdown-item:not(:first-child):not(:last-child):hover {
  border-radius: 0;  /* Maintain no rounded corners on hover */
}

/* Last item - bottom corners rounded */
.dropdown-item.last-item,
.dropdown-item:last-child {
  border-radius: 0 0 12px 12px;  /* Bottom-left, bottom-right rounded */
}

.dropdown-item.last-item:hover,
.dropdown-item:last-child:hover {
  border-radius: 0 0 12px 12px;  /* Maintain rounded bottom corners on hover */
}
```

**Result:**
- First item: Top corners rounded (`12px 12px 0 0`), bottom corners NOT rounded
- Middle items: NO rounded corners (square)
- Last item: Top corners NOT rounded, bottom corners rounded (`0 0 12px 12px`)

---

### Corner Rounding Summary

| Number of Items | First Item | Middle Items | Last Item |
|----------------|------------|--------------|-----------|
| **1 item** | All corners round (`12px`) | N/A | N/A |
| **2 items** | Top corners round (`12px 12px 0 0`) | N/A | Bottom corners round (`0 0 12px 12px`) |
| **3+ items** | Top corners round (`12px 12px 0 0`) | No round corners (`0`) | Bottom corners round (`0 0 12px 12px`) |

**Key Rules:**
- Always add `.first-item` class to the first item
- Always add `.last-item` class to the last item
- Rounded corners must match the dropdown menu's `border-radius` (12px)
- Corner rounding is preserved on hover

---

### Icon Styling

#### Base Icon Styles

```css
.dropdown-item i {
  width: 20px;  /* Fixed width for alignment */
  text-align: center;
  color: var(--dash-text-light);  /* #94a3b8 - muted gray */
  font-size: 1.1rem;  /* Slightly larger than text */
  flex-shrink: 0;  /* Prevent icon from shrinking */
}
```

#### Icon Hover State

```css
.dropdown-item:hover i {
  color: var(--dash-primary);  /* #10b981 - green on hover */
}
```

**Icon Guidelines:**
- Use Font Awesome icons (`fas fa-*`)
- Fixed width of `20px` ensures consistent alignment
- Icons are muted gray by default (`var(--dash-text-light)`)
- Icons turn green on hover (`var(--dash-primary)`)
- Icons should be centered within their fixed width
- **Note:** Icons are optional - use only when needed (typically for navigation menus, not form inputs)

---

### Divider Styling

```css
.dropdown-divider {
  height: 1px;
  background: rgba(0,0,0,0.1);  /* Light gray line */
  margin: 0;  /* No margin */
  padding: 0;  /* No padding */
}
```

**Usage:**
- Place dividers between logical groups of items
- Typically used before logout/action items
- No spacing around dividers (they sit flush with items)

---

### Form Items (e.g., Logout)

```css
.dropdown-item-form {
  display: block;
  width: 100%;
  text-align: left;
}

.dropdown-item-form .dropdown-item {
  /* Inherits all .dropdown-item styles */
  margin-top: 0;  /* No extra margin */
}
```

**Note:** Form items (like logout buttons) should use the same styling as regular items, wrapped in a form element.

---

## Color Variables

Use these CSS variables for consistency:

```css
:root {
  --dash-primary: #10b981;           /* Green - primary color */
  --dash-primary-hover: #059669;     /* Darker green for hover */
  --dash-text-main: #1e293b;          /* Dark text */
  --dash-text-light: #94a3b8;        /* Muted gray for icons */
  --dash-border: #e2e8f0;             /* Light border color */
}
```

---

## Spacing Guidelines

### Padding

- **Container**: `padding: 0` (NO padding on dropdown menu container)
- **Items**: `padding: 12px 20px` (12px vertical, 20px horizontal)
- **Gap between icon and text**: `12px`

### Margins

- **Menu offset from trigger**: `top: calc(100% + 8px)` (8px gap)
- **Items**: No margin (padding handles spacing)
- **Divider**: No margin

---

## Animation & Transitions

### Menu Appearance

```css
.dropdown-menu {
  opacity: 0;
  visibility: hidden;
  transform: translateY(-10px);
  transition: all 0.2s ease;
}

.dropdown-container.active .dropdown-menu {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}
```

### Item Hover

```css
.dropdown-item {
  transition: background 0.2s ease;
}
```

**Animation Details:**
- Menu slides down 10px and fades in
- Smooth 0.2s ease transition
- Items have smooth background color transition on hover

---

## JavaScript Implementation

### Form Input Dropdown (Custom Select)

```javascript
document.addEventListener('DOMContentLoaded', function() {
  const trigger = document.getElementById('dropdownTrigger');
  const menu = document.getElementById('dropdownMenu');
  const hiddenInput = document.getElementById('hiddenInput');
  const selectedText = document.getElementById('selectedText');
  const container = document.querySelector('.custom-dropdown-container');

  if (trigger && menu) {
    // Toggle dropdown
    trigger.addEventListener('click', function(e) {
      e.stopPropagation();
      container.classList.toggle('active');
    });

    // Handle item selection
    const dropdownItems = menu.querySelectorAll('.dropdown-item');
    dropdownItems.forEach(item => {
      item.addEventListener('click', function() {
        const value = this.getAttribute('data-value');
        const text = this.querySelector('span').textContent;
        
        hiddenInput.value = value;
        selectedText.textContent = text;
        
        // Update active state
        dropdownItems.forEach(i => i.classList.remove('active'));
        this.classList.add('active');
        
        // Close dropdown
        container.classList.remove('active');
      });
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', function(event) {
      if (container && !container.contains(event.target)) {
        container.classList.remove('active');
      }
    });

    // Mark current selection as active
    const currentValue = hiddenInput.value;
    dropdownItems.forEach(item => {
      if (item.getAttribute('data-value') === currentValue) {
        item.classList.add('active');
      }
    });
  }
});
```

### Navigation/Action Dropdown

```javascript
document.addEventListener('DOMContentLoaded', function() {
  const trigger = document.getElementById('dropdownTrigger');
  const menu = document.getElementById('dropdownMenu');
  const container = document.querySelector('.dropdown-container');

  if (trigger && menu) {
    // Toggle dropdown
    trigger.addEventListener('click', function(e) {
      e.stopPropagation();
      container.classList.toggle('active');
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', function(event) {
      if (container && !container.contains(event.target)) {
        container.classList.remove('active');
      }
    });
  }
});
```

**Key JavaScript Patterns:**
- Use `e.stopPropagation()` on trigger click to prevent immediate closing
- Toggle `.active` class on container to show/hide menu
- Close dropdown when clicking outside the container
- For form inputs, update hidden input and selected text display
- Mark active/selected items with `.active` class

---

## Example: Form Input Dropdown (Custom Select)

### HTML

```html
<div class="custom-dropdown-container">
  <button type="button" class="custom-dropdown-trigger" id="mentorTypeTrigger">
    <span class="dropdown-selected-text" id="mentorTypeSelected">
      Select mentor type
    </span>
    <i class="fas fa-chevron-down"></i>
  </button>
  <input type="hidden" name="mentor_type" id="mentorTypeInput" value="">
  <div class="custom-dropdown-menu" id="mentorTypeMenu">
    <button type="button" class="dropdown-item first-item" data-value="life_coach">
      <span>Life Coach</span>
    </button>
    <button type="button" class="dropdown-item" data-value="career_coach">
      <span>Career Coach</span>
    </button>
    <button type="button" class="dropdown-item last-item" data-value="business_coach">
      <span>Business Coach</span>
    </button>
  </div>
</div>
```

### CSS

```css
.custom-dropdown-container {
  position: relative;
  width: 100%;
}

.custom-dropdown-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 10px 16px;
  background: white;
  border: 1px solid var(--dash-border);
  border-radius: 8px;
  color: var(--dash-text-main);
  font-size: 0.95rem;
  font-weight: 400;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.custom-dropdown-menu {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
  padding: 0; /* ⚠️ NO PADDING */
  opacity: 0;
  visibility: hidden;
  transform: translateY(-10px);
  transition: all 0.2s ease;
  z-index: 10005;  /* ⚠️ IMPORTANT: High z-index to appear above modals, footers, and other UI elements */
  min-width: 100%;
}

.custom-dropdown-container.active .custom-dropdown-menu {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  color: var(--dash-text-main);
  text-decoration: none;
  transition: background 0.2s ease;
  border: none;
  background: transparent;
  width: 100%;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 400;
  text-align: left;
}

.dropdown-item.first-item {
  border-radius: 12px 12px 0 0;
}

.dropdown-item.last-item {
  border-radius: 0 0 12px 12px;
}

.dropdown-item:hover {
  background: rgba(16, 185, 129, 0.1);
  color: var(--dash-primary);
}

.dropdown-item.first-item:hover {
  border-radius: 12px 12px 0 0;
}

.dropdown-item.last-item:hover {
  border-radius: 0 0 12px 12px;
}
```

---

## Example: Navigation Dropdown Menu

### HTML

```html
<div class="user-profile-dropdown">
  <button class="user-profile-trigger" id="userProfileTrigger">
    <span class="user-name">John Doe</span>
    <div class="user-avatar">...</div>
  </button>
  <div class="user-dropdown-menu" id="userDropdownMenu">
    <a href="/account/" class="dropdown-item first-item">
      <i class="fas fa-user"></i>
      <span>Account</span>
    </a>
    <a href="/settings/" class="dropdown-item">
      <i class="fas fa-cog"></i>
      <span>Settings</span>
    </a>
    <div class="dropdown-divider"></div>
    <form action="{% url 'accounts:logout' %}" method="post" class="dropdown-item-form">
      {% csrf_token %}
      <button type="submit" class="dropdown-item logout-item last-item">
        <i class="fas fa-sign-out-alt"></i>
        <span>Logout</span>
      </button>
    </form>
  </div>
</div>
```

### CSS

```css
.user-profile-dropdown {
  position: relative;
}

.user-dropdown-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
  min-width: 200px;
  padding: 0;  /* ⚠️ NO PADDING */
  opacity: 0;
  visibility: hidden;
  transform: translateY(-10px);
  transition: all 0.2s ease;
  z-index: 10005;  /* ⚠️ IMPORTANT: High z-index to appear above modals, footers, and other UI elements */
}

.user-profile-dropdown.active .user-dropdown-menu {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  color: var(--dash-text-main);
  text-decoration: none;
  transition: background 0.2s ease;
  border: none;
  background: transparent;
  width: 100%;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 400;
}

.dropdown-item.first-item {
  border-radius: 12px 12px 0 0;
}

.dropdown-item.last-item {
  border-radius: 0 0 12px 12px;
}

.dropdown-item:hover {
  background: rgba(16, 185, 129, 0.1);
  color: var(--dash-primary);
}

.dropdown-item.first-item:hover {
  border-radius: 12px 12px 0 0;
}

.dropdown-item.last-item:hover {
  border-radius: 0 0 12px 12px;
}

.dropdown-item i {
  width: 20px;
  text-align: center;
  color: var(--dash-text-light);
  font-size: 1.1rem;
  flex-shrink: 0;
}

.dropdown-item:hover i {
  color: var(--dash-primary);
}

.dropdown-divider {
  height: 1px;
  background: rgba(0,0,0,0.1);
}
```

---

## Checklist for New Dropdown Menus

When creating a new dropdown menu, ensure:

### General Requirements
- [ ] Container has `padding: 0` (no padding on dropdown menu)
- [ ] Items have `padding: 12px 20px`
- [ ] Font size is `0.95rem`
- [ ] Font weight is `400` (normal)
- [ ] First item has `.first-item` class
- [ ] Last item has `.last-item` class
- [ ] Corner rounding follows the rules based on number of items (see table above)
- [ ] Hover background is `rgba(16, 185, 129, 0.1)` (light green) for navigation/action dropdowns OR `#f1f5f9` (light grey) for form input dropdowns
- [ ] Hover text color is `var(--dash-primary)` (#10b981) for navigation/action dropdowns OR `#1e293b` (dark) for form input dropdowns
- [ ] Gap between icon and text is `12px`
- [ ] Border radius matches menu container (`12px`)
- [ ] Smooth transitions (`0.2s ease`)
- [ ] Proper z-index for layering (`10005` - high enough to appear above modals, footers, and other UI elements)

### Form Input Dropdowns
- [ ] Trigger has white background (no background color change on hover)
- [ ] Trigger hover only changes border color to green
- [ ] Hidden input field is included for form submission
- [ ] Selected text is displayed in trigger
- [ ] Chevron icon rotates 180° when active

### Navigation/Action Dropdowns
- [ ] Icons are `20px` wide, centered, gray by default, green on hover
- [ ] Icons use Font Awesome (`fas fa-*`)
- [ ] Dividers are used appropriately between groups

### Row-Action Dropdowns (scrollable lists)
- [ ] Use the exact structure in the [Row-Action Dropdowns](#row-action-dropdowns-scrollable-lists) section: `.dropdown` → `.session-action-btn` + `.dropdown-menu` (siblings), and `toggleDropdown(this)` on the trigger
- [ ] Dropdown lives inside a supported scroll context (`.session-timeline-container`, `#stagesList`, or a container added in base template)
- [ ] Do not add custom open/close or positioning JS; use global `toggleDropdown` and `clearSessionDropdownFixed` only
- [ ] If the trigger is shown only on row hover, use `:has(.dropdown-menu.show)` so it stays visible while the menu is open

---

## Common Mistakes to Avoid

1. **❌ Adding padding to dropdown menu container** - Padding should only be on items
2. **❌ Forgetting rounded corners on first/last items** - Always add `.first-item` and `.last-item` classes
3. **❌ Not maintaining rounded corners on hover** - Hover state must preserve corner rounding
4. **❌ Wrong corner rounding for number of items** - Follow the rules: 1 item = all round, 2 items = first top round/last bottom round, 3+ items = first top round/middle square/last bottom round
5. **❌ Adding background color to form input trigger on hover** - Only border color should change
6. **❌ Inconsistent icon widths** - Always use `width: 20px` for icons
7. **❌ Wrong hover colors** - Use light green background (`rgba(16, 185, 129, 0.1)`) for navigation/action dropdowns, or light grey (`#f1f5f9`) for form input dropdowns
8. **❌ Missing transitions** - Always include smooth transitions for better UX
9. **❌ Not handling single/two item cases** - Corner rounding must adapt to number of items
10. **❌ Row-action dropdowns: custom structure or JS** - Inside scrollable lists use only the standard structure (`.dropdown`, `.session-action-btn`, `.dropdown-menu`) and global `toggleDropdown(this)`; do not implement your own fixed positioning or scroll logic.
11. **❌ Row-action dropdown: trigger disappears when menu is open** - If the trigger is visible only on row hover, add a rule so the trigger (or its wrapper) stays visible when the menu is open, e.g. `.row-actions:has(.dropdown-menu.show) { opacity: 1; }`.

---

## Notes

- This style guide is based on the navbar avatar dropdown menu implementation
- All dropdown menus should follow these patterns for consistency
- The `padding: 0` on the container is critical for proper rounded corner behavior
- Corner rounding rules are essential for proper visual appearance
- Form input triggers should NOT have background color changes on hover
- Icons should always use Font Awesome (`fas fa-*`) when used
- Colors use CSS variables for easy theming
- This guide covers form inputs, navigation/action dropdowns, and **row-action dropdowns** (three-dots menus in scrollable lists). For the latter, follow the [Row-Action Dropdowns](#row-action-dropdowns-scrollable-lists) section so fixed positioning and scroll repositioning work correctly.
