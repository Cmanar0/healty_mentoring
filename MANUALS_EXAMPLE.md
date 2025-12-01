# Manuals Field - Example Data

## Data Structure

The `manuals` field is a JSON array containing tutorial bubble objects. Each object has the following structure:

```json
{
  "id": "dom_element_id",
  "title": "Bubble Title",
  "text": "Description text for the tutorial bubble",
  "position": {"x": 0, "y": 0} | "top" | "bottom" | "left" | "right",
  "displayed": false
}
```

**Important Notes:**
- `id` must match the `id` attribute of a DOM element on the page (e.g., `id="createNewSection"`)
- `position` can be:
  - An object with `x` and `y` coordinates relative to the target element (e.g., `{"x": 0, "y": -20}`)
  - A string: `"top"`, `"bottom"`, `"left"`, or `"right"` (for backward compatibility)

## Example Data for Testing

Copy and paste this JSON into the `manuals` field in Django admin:

### For Mentor Dashboard:

**Important:** You must add `id` attributes to the elements you want to highlight. For example:

```html
<div class="create-new-section" id="createNewSection">
  ...
</div>
```

Then use this JSON:

```json

[
  {
    "id": "createNewSection",
    "title": "Create New Content",
    "text": "Use these buttons to quickly create sessions, users, projects, marketing materials, and blog posts.",
    "position": {"x": -350, "y": 0},
    "displayed": false
  },
  {
    "id": "statsCard",
    "title": "Track Your Performance",
    "text": "View your statistics and metrics here. Use the dropdown to filter by different time periods.",
    "position": {"x": 0, "y": 300},
    "displayed": false
  },
  {
    "id": "backlogCard",
    "title": "Your Backlog",
    "text": "Items that require your action are displayed here. Stay on top of your tasks!",
    "position": {"x": 0, "y": -180},
    "displayed": false
  }
]
```

### For User Dashboard:

```json
[
  {
    "id": "my_mentors_card",
    "title": "Find Your Mentors",
    "text": "Browse and connect with mentors who can help you achieve your goals.",
    "selector": ".dashboard-card:has(.card-title:contains('My Mentors'))",
    "position": "bottom",
    "displayed": false
  },
  {
    "id": "tasks_card",
    "title": "Your Tasks",
    "text": "Keep track of tasks you need to complete. Check them off as you finish!",
    "selector": ".dashboard-card:has(.card-title:contains('Tasks to Do'))",
    "position": "left",
    "displayed": false
  }
]
```

## Field Descriptions

- **id**: The `id` attribute of the DOM element to highlight (string). **Must match an actual `id` on an element in your HTML.**
- **title**: The heading text displayed in the tutorial bubble (string).
- **text**: The description/body text displayed in the tutorial bubble (string).
- **position**: Where to position the bubble relative to the target element. Can be:
  - **Object with coordinates**: `{"x": 0, "y": -20}` - Position relative to the top-left corner of the target element (in pixels)
    - `x`: Horizontal offset (positive = right, negative = left)
    - `y`: Vertical offset (positive = down, negative = up)
  - **String** (for backward compatibility): `"top"`, `"bottom"`, `"left"`, or `"right"`
- **displayed**: Boolean flag indicating if this manual has been shown (boolean). Set to `false` for new manuals. The system automatically removes displayed manuals from the array.

## How It Works

1. When a user logs in, the system checks for manuals with `displayed: false`
2. Tutorial bubbles appear one at a time, pointing to the specified elements
3. Users can close bubbles by clicking the X button or clicking outside the bubble
4. When closed, the manual is marked as displayed and removed from the array
5. The next manual in the array is shown automatically (if available)
6. Once all manuals are displayed, they won't appear again

## Testing Tips

- Set `displayed: false` for all manuals you want to test
- Use browser developer tools to find the correct CSS selectors for elements
- Test different positions to see which works best for each element
- The system will automatically skip manuals if the target element is not found on the page

