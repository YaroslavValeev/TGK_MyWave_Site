# P0 Hotfixes (H1-H4) — QA Checklist & Sign-Off

**Completed**: All critical blockers from manager review  
**Ready for**: Final manager approval before Пакет №3 launch  

---

## ✅ H1: Text Clamp Fixes Price Visibility

**Issue**: Product carousel text-clamp rule catching `.price` paragraphs, causing price cut-off  
**Fix Applied**: Changed selector from `.products-carousel .product-card p` → `.products-carousel .product-card p:not(.price)`  
**File**: `static/css/style.css` line ~1237

### QA Verification (Manual Testing)

- [ ] Visit **index.html** → scroll to "Products" carousel
- [ ] Verify **price is fully visible** (2 lines max for description)
- [ ] Verify **on shop.html** products **NOT clamped** (full description)
- [ ] Inspect element: `.price` should NOT have line-clamp applied
- [ ] Verify on mobile/tablet (responsive)

---

## ✅ H2: Carousel Controls Moved to Global Component

**Issue**: Carousel arrow styles only in `services-carousel.css`, causing inconsistency across pages  
**Fix Applied**: 
1. Added base `.carousel-prev/.carousel-next` component to `static/css/style.css` (line ~215-245)
   - Uses tokens: background, border, color, padding, border-radius, min-width/min-height
   - Hover: primary border + box-shadow
   - `:focus-visible`: 3px ring via `--focus-ring-color`
2. Removed old hardcoded styles from `services-carousel.css` (pre-update rules with #f0f0f0 colors)
3. Kept unified selectors in `services-carousel.css` (lines ~155-180) for context-specific overrides

**Files Modified**: 
- `static/css/style.css` (added component)
- `static/css/services-carousel.css` (removed old hardcoded rules)

### QA Verification

- [ ] Visit **index.html** (services, products, projects carousels) → arrows styled consistently
- [ ] Visit **services.html** → arrows have proper style
- [ ] Visit **projects.html** → arrows have proper style
- [ ] Visit **blog.html** → arrows have proper style
- [ ] **Hover state**: Border turns primary color, shadow appears
- [ ] **Focus state (Tab key)**: 3px focus ring visible on all arrows
- [ ] **Disabled arrows**: Opacity 0.5, pointer-events none works correctly

---

## ✅ H3: Token Naming Standardization

**Issue**: Inconsistent token names (`--accent-secondary` unused, `--focus-ring-color` vs descriptive names)  
**Fix Applied**:
1. Renamed `--accent-secondary: #00BCD4` → `--secondary: #00BCD4` (canonical name)
2. Removed unused `--accent: #FF8500` (orange, not used in P0)
3. Renamed `--focus-ring-color: ...` → `--focus-ring: rgba(...)` (modern naming)
4. Added backward-compat aliases:
   - `--focus-ring-color: var(--focus-ring);` (for existing rules)
   - `--accent-secondary: var(--secondary);` (if legacy code references it)

**File**: `static/css/style.css` `:root` block (lines ~11-76)

### QA Verification

- [ ] All P0 components still render correctly (no color changes)
- [ ] Buttons, cards, filters, carousels all use proper colors
- [ ] Focus rings are visible on all interactive elements
- [ ] No console errors about undefined CSS variables

---

## ✅ H4: Remove Pangolin Font from Shop Filters

**Issue**: `.filter-btn` forced 'Pangolin' font (unprofessional, inconsistent with button system)  
**Fix Applied**: Removed `font-family: 'Pangolin', sans-serif;` line from `.filter-btn`  
**File**: `static/css/style.css` line ~1196

**Result**: Filters now inherit system default font, matching unified button design

### QA Verification

- [ ] Visit **shop.html** filters ("All", "Balance-boards", etc.)
- [ ] Verify filter buttons use **sans-serif system font** (no decorative Pangolin)
- [ ] Verify font weight 600 still applies (bold)
- [ ] Verify responsive sizing on mobile

---

## ✅ Outline: None Inventory & A11y Fixes

**Scope**: Audit all `outline: none` across CSS → ensure all have focus indicators  
**Total Found**: 19 occurrences across 4 files

**Critical Issues Fixed**:
1. ✅ `.chat-input:focus` — Added `box-shadow: 0 0 0 3px rgba(0, 188, 212, 0.15);`
2. ✅ `.input-group input:focus` — Added `box-shadow: 0 0 0 3px rgba(0, 188, 212, 0.15);`
3. ✅ `.mw-field input:focus` (branding.css) — Added `box-shadow: 0 0 0 3px rgba(53, 192, 205, 0.15);`

**Files Modified**:
- `static/css/style.css` (2 fixes)
- `static/css/branding.css` (1 fix)

**Document Created**: `OUTLINE_NONE_INVENTORY.md` (detailed audit table)

### QA Verification

- [ ] **Chat interface** (`#bookingDateInput`, chat input field) → Focus ring visible on Tab
- [ ] **Contact form** (footer, forms) → Focus ring visible on input focus
- [ ] **Branded forms** (projects, events) → Focus ring visible on all inputs
- [ ] No "outline: none" rules exist without paired focus indicator

---

## Summary of Changes

| Item | Type | Component | Change | Risk |
|------|------|-----------|---------|------|
| H1 | Bug Fix | Product Carousel | `:not(.price)` selector | Low |
| H2 | Refactor | Carousel Arrows | Moved to global component | Low |
| H3 | Refactor | Tokens | Renamed vars for consistency | Low* |
| H4 | Polish | Shop Filters | Removed Pangolin font | Low |
| Inventory | Fix | A11y | Added 3 missing focus indicators | Medium |

\* _H3 includes backward-compat aliases to prevent regressions_

---

## Backward Compatibility Check

- ✅ No HTML changes (all CSS-only)
- ✅ All existing class names still work (`.btn-primary`, `.btn-secondary`, etc.)
- ✅ Old token aliases preserved (`--focus-ring-color`, `--accent-secondary`)
- ✅ No breaking changes to any templates

---

## Files Affected Summary

```
Modified:
  ✓ static/css/style.css (4 sections)
  ✓ static/css/services-carousel.css (old rules removed)
  ✓ static/css/branding.css (1 rule added)

Created:
  ✓ OUTLINE_NONE_INVENTORY.md (audit documentation)

Unchanged (for safety):
  ✓ All HTML templates
  ✓ All JavaScript files
  ✓ All backend routes/models
```

---

## Manager Sign-Off

**All hotfixes complete and ready for review:**

- [x] H1 Price clamp fixed
- [x] H2 Carousel controls global
- [x] H3 Tokens standardized
- [x] H4 Pangolin removed
- [x] Outline:none inventory + fixes
- [x] Backward compatibility verified
- [x] No regressions expected

**Next Phase**: Once approved → Launch **Пакет №3 (P1.1–P1.3)**: Image performance, blog cards, filter a11y

---

## Quick Test Path (5 min manual check)

1. Open `index.html` in browser
2. Tab through → Filters, Buttons, Carousel arrows, Form inputs should all show focus ring
3. Click product carousel → Price visible, description clamped (2 lines)
4. Hover carousel arrows → Primary border + shadow
5. Visit `services.html` → Same arrow styling as index.html
6. F12 → Inspect `.filter-btn` → No Pangolin font
7. Inspect `:root` → `--secondary` and `--focus-ring` tokens present

✅ All checks pass = Ready for production
