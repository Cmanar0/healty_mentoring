# Dropdown Menu Style Guide

This document describes the standard styling and structure for dropdown menus in the Healthy Mentoring application. Use this as a reference when creating new dropdown menus to ensure consistency across the application.

## Overview

This guide covers dropdown menus in two main scenarios:
1. **Form Input Dropdowns** - Custom styled select inputs for forms (e.g., Mentor Type selector)
2. **Navigation/Action Dropdowns** - Dropdown menus triggered by clicking any element (e.g., user profile menu, notification menu)

All dropdown menus should follow the styling patterns established in the navbar avatar dropdown menu. This guide covers font styling, hover effects, rounded corners, icon styling, spacing, and trigger element styling.

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
  z-index: 1000;
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

```css
.dropdown-item:hover {
  background: rgba(16, 185, 129, 0.1);  /* Light green background */
  color: var(--dash-primary);  /* #10b981 - green text */
}
```

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
  z-index: 1000;
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
  z-index: 1000;
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
- [ ] Hover background is `rgba(16, 185, 129, 0.1)` (light green)
- [ ] Hover text color is `var(--dash-primary)` (#10b981)
- [ ] Gap between icon and text is `12px`
- [ ] Border radius matches menu container (`12px`)
- [ ] Smooth transitions (`0.2s ease`)
- [ ] Proper z-index for layering (`1000`)

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

---

## Common Mistakes to Avoid

1. **❌ Adding padding to dropdown menu container** - Padding should only be on items
2. **❌ Forgetting rounded corners on first/last items** - Always add `.first-item` and `.last-item` classes
3. **❌ Not maintaining rounded corners on hover** - Hover state must preserve corner rounding
4. **❌ Wrong corner rounding for number of items** - Follow the rules: 1 item = all round, 2 items = first top round/last bottom round, 3+ items = first top round/middle square/last bottom round
5. **❌ Adding background color to form input trigger on hover** - Only border color should change
6. **❌ Inconsistent icon widths** - Always use `width: 20px` for icons
7. **❌ Wrong hover colors** - Use light green background (`rgba(16, 185, 129, 0.1)`), not dark
8. **❌ Missing transitions** - Always include smooth transitions for better UX
9. **❌ Not handling single/two item cases** - Corner rounding must adapt to number of items

---

## Notes

- This style guide is based on the navbar avatar dropdown menu implementation
- All dropdown menus should follow these patterns for consistency
- The `padding: 0` on the container is critical for proper rounded corner behavior
- Corner rounding rules are essential for proper visual appearance
- Form input triggers should NOT have background color changes on hover
- Icons should always use Font Awesome (`fas fa-*`) when used
- Colors use CSS variables for easy theming
- This guide covers both form inputs and navigation/action dropdowns
