# Alias Bugs

## Bug 1 (CRITICAL): CSRF blocks alias saves — modifying aliases does not work

- **File:** `streetsign_server/views/__init__.py:66-72` (CSRF exempt list), `streetsign_server/static/alias_editor.js:72-79` (save POST)
- **Cause:** `POST /aliases` (`save_aliases` endpoint) is not in the CSRF exempt endpoint list. `alias_editor.js` sends `$.post('/aliases', ...)` without a `_csrf_token`. Every save attempt is silently rejected with 403.
- **Fix:** Add `'save_aliases'` to the CSRF exempt endpoint list in `views/__init__.py`.

## Bug 2 (MEDIUM): Silently wrong layout fallback — settings/layout don't load properly

- **File:** `streetsign_server/static/alias_editor.js:31`
- **Cause:** When the `screen_name` saved in an alias no longer matches any existing screen (deleted/renamed), `makeAliasesEditor` silently falls back to `screenNames[0]` with no warning.
  ```javascript
  screen_name: screenNames.includes(resolvedScreen) ? resolvedScreen : screenNames[0],
  ```
- **Fix:** Preserve the original name in the select options (rather than falling back silently) or add a visible warning indicator.

## Bug 3 (MEDIUM): Dashboard 500 crash with orphaned aliases

- **File:** `streetsign_server/templates/dashboard.html:208`, `streetsign_server/views/__init__.py:122-123`
- **Cause:** When a screen referenced by an alias is deleted, `alias['screen']` becomes `None` (line 123). `dashboard.html:208` accesses `client.screen.background` without a null guard.
  ```jinja2
  {% if client.screen.background %}
  ```
- **Fix:** Add null guard: `{% if client.screen and client.screen.background %}`.

## Bug 4 (LOW): Empty alias names bypass duplicate check

- **File:** `streetsign_server/views/screens.py:258-259`
- **Cause:** The list comprehension filters out empty/whitespace names before the duplicate check, allowing multiple aliases with empty names to be saved.
  ```python
  names = [a.get('name', '').strip()
           for a in aliases_list if a.get('name', '').strip()]
  if len(names) != len(set(names)):
  ```
- **Fix:** Validate empty names separately (reject with an error) before the dedup check, or don't filter empty names and let them collide.
