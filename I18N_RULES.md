# i18n Rules (TR/EN)

This project supports Turkish and English with session-based language switching.

## Required for every new page

1. Template must extend `base.html` so the top-right language selector is available.
2. Do not hardcode visible UI text in templates.
3. Use `{{ t('key_name') }}` for every label, heading, button, and static message.
4. If backend sends labels/details to templates, use `_t('key_name')` in `app.py`.
5. Add every new key to both dictionaries in `TRANSLATIONS` in `app.py`:
   - `TRANSLATIONS['en']`
   - `TRANSLATIONS['tr']`
6. Keep key names lowercase with underscores, e.g. `student_exam_title`.
7. After changes, run:

```powershell
./check_i18n.ps1
```

## Quick page skeleton

```html
{% extends "base.html" %}
{% block title %}{{ t('new_page_title') }}{% endblock %}
{% block content %}
<h1>{{ t('new_page_title') }}</h1>
<p>{{ t('new_page_description') }}</p>
{% endblock %}
```

## Notes

- Brand names (for example university name) may remain unchanged.
- If a key is missing, fallback displays the key text. Always add proper translations.
