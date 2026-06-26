# Changelog

Based on StreetSign Server by Daniel Fairhead (2013–2019) and Daniel Lang (2020–2024).

## Security & Hardening
- Fixed a feed group-permission bug where users could inherit read/write/publish
  rights from groups they did not belong to.
- `Feed.grant()` is now additive — granting one permission no longer silently
  revokes the others a user or group already holds.
- Reworked password hashing: passwords are SHA-256 pre-hashed (so they aren't
  truncated at bcrypt's 72-byte limit) and bcrypt-hashed with a per-password
  salt. Hashes no longer mix in `SECRET_KEY`, so it can be rotated and databases
  moved between installs without locking users out.
- The server now refuses to start in production with the insecure default
  `SECRET_KEY`.
- The development server's interactive debugger is now off by default; it must
  be enabled with `FLASK_DEBUG=1`, and only binds to `127.0.0.1` when enabled.
- Implemented account lockout after repeated failed logins (`MAX_FAILED_LOGINS`,
  default 10).
- Added SSRF protection to server-side fetches (RSS feeds and external images):
  non-`http(s)` schemes and private/loopback/link-local addresses are rejected,
  and the image fetch script is restricted to http/https with size/time limits.
- Local-folder image import now copies files directly instead of fetching
  `file://` URLs.
- Restricted the RSS importer's allowed HTML tags to a safe set regardless of
  per-feed configuration.
- Escaped user-controlled content in image thumbnails, the uploaded-files
  listing, and the generated `fonts.css` (prevents stored XSS / CSS injection).
- Login and logout are no longer exempt from CSRF protection.
- Authentication is now enforced on the feed and post-type editor pages, and
  directories are no longer created on GET requests.
- Fixed the Web Hook post type's URL scheme handling.

## Default install
- A fresh database now seeds three demo users (`admin`, `editor`, `viewer`,
  each with a password matching the login name) and `admins`/`editors` groups,
  example feeds and posts, and a ready-to-use two-zone "Default" screen.

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
