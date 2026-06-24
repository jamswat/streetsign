# Changelog

Based on StreetSign Server by Daniel Fairhead (2013–2019) and Daniel Lang (2020–2024).

## Modernization
- Replaced Knockout.js with Alpine.js (44KB, zero-build, same MVVM paradigm)
- Replaced Spectrum color picker with native `<input type="color">`
- Replaced jQuery Cookie with localStorage API
- Removed abandoned Intel AppFramework mobile UI (3,500+ lines)
- Rebuilt mobile screen with vanilla CSS flexbox and modern JS

## CSS
- Added CSS custom properties (variables) to all stylesheets
- Replaced table-cell and float-based layouts with flexbox
- Removed unnecessary vendor prefixes (-webkit, -moz)
- Added prefers-reduced-motion media query for accessibility
- Removed dead selectors and duplicate inline styles
- Fixed heading display:inline bug that broke all page headings

## HTML & Accessibility
- Added `<meta charset="utf-8">`, `<html lang="en">`, `<meta name="theme-color">`
- Added `<th scope="col">` to all tables
- Added `aria-label`, `aria-hidden`, `role="alert"` throughout
- Fixed missing label/id associations on login form
- Added `loading="lazy"` to images
- Added `<table-responsive>` wrappers to all tables
- Fixed unclosed tags and malformed markup in templates

## JavaScript
- All files: `var` → `const`/`let`, `function` → arrow functions, string concatenation → template literals
- Added `'use strict'` consistently
- Added CSRF protection to all forms and AJAX requests

## Rich Text Editor
- Move to Quill v2 (zero jQuery dependency)

## Features
- Added "Show permanently" post option
- Added video post type with optional audio overlay
- Added raw HTML post type with Prism.js syntax highlighting
- Added external data source test button


## Upgraded Libraries
- jQuery 1.10.1 → 3.x
- Bootstrap 3 → 5.3
- Prism → 1.30
- Moment.js → Day.js
- Choices.js (added)
- Alpine.js (added)
