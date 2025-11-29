# Healthy Mentoring Design System & Philosophy

## 🎨 Design Philosophy
Our design philosophy is built on three pillars, driven by our cross-functional "Dream Team":

### 1. The "Premium & Trust" Aesthetic (UI Team)
*   **Visual Language**: Clean, modern, and trustworthy. We use a lot of whitespace to let the content breathe.
*   **Glassmorphism**: We use subtle glass effects (`backdrop-filter: blur`) to create depth and a modern feel, especially on overlays and cards.
*   **Gradients**: Our brand uses a signature Emerald-to-Blue gradient (`linear-gradient(135deg, #10b981 0%, #3b82f6 100%)`) for primary actions and key text to signify energy and growth.
*   **Typography**:
    *   **Headings**: `Outfit` (Bold, Modern) - Used for impact and structure.
    *   **Body**: `Inter` (Clean, Readable) - Used for high legibility in long-form content.

### 2. The "Success-First" Experience (UX/Sales Team)
*   **Dashboard Goal**: When a user (Mentor or Mentee) logs in, they should immediately feel *successful* and *oriented*.
*   **Action-Oriented**: Key actions (e.g., "Join Session", "Find Mentor") are always prominent and use our primary gradient.
*   **Progress Visualization**: We don't just show numbers; we show *progress*. Use visual indicators like progress bars or rising graphs to motivate users.
*   **Personalization**: Always address the user by name and show relevant context (e.g., "Good Morning, Marian").

### 3. The "Scalable System" (Engineering Team)
*   **CSS Variables**: We rely heavily on `:root` variables in `main.css` for consistency.
*   **Component-Based**: We build reusable components (Cards, Buttons, Badges) rather than one-off styles.
*   **Mobile-First**: Every design must look stunning on a phone before it's approved for desktop.

---

## 🛠 Component Library

### Colors
*   **Primary**: Emerald Green (`#10b981`) - Growth, Health.
*   **Secondary**: Slate Dark (`#0f172a`) - Professionalism, Stability.
*   **Accent**: Blue (`#3b82f6`) - Trust, Technology.
*   **Background**: Slate Light (`#f8fafc`) - Clean canvas.

### Cards
*   **Standard Card**: White background, `border-radius: 16px`, subtle shadow (`box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1)`).
*   **Hover Effect**: Lift up (`transform: translateY(-4px)`) and increased shadow on hover.

### Buttons
*   **Primary**: Gradient background, rounded pills (`border-radius: 50px`), white text.
*   **Secondary**: White background, border, dark text.
*   **Ghost**: Transparent background, text only (for less important actions).

### Typography
*   **H1**: `Outfit`, 2.5rem+, Bold.
*   **H2**: `Outfit`, 2rem, Semi-Bold.
*   **Body**: `Inter`, 1rem, Regular.

### Dropdown Menus
Universal dropdown component for actions.

**HTML Structure:**
```html
<div class="dropdown">
  <button class="action-btn" onclick="toggleDropdown(this)">...</button>
  <div class="dropdown-menu">
    <button class="dropdown-item">Action 1</button>
    <button class="dropdown-item">Action 2</button>
  </div>
</div>
```

**Features:**
- **Rounded Corners**: First item has top rounded corners, last item has bottom rounded corners.
- **No Padding**: Container has no padding; items provide padding.
- **Hover Effect**: Items change background color on hover.

---

## 🚀 Implementation Guide for New Pages
1.  **Start with the Grid**: Use CSS Grid for layout (`display: grid; grid-template-columns: ...`).
2.  **Use the Variables**: Never hardcode hex values. Use `var(--primary)`, `var(--text-dark)`, etc.
3.  **Add "Delight"**: Add simple transitions (`transition: all 0.3s ease`) to interactive elements.
4.  **Check Mobile**: Resize your browser to 375px width. Does it still look good?

---

> **"If it doesn't look like a million-dollar SaaS, it's not ready."** - *Head of Design*
