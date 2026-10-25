# Detected Project Patterns

- **Django apps and structure:** The project configuration is in `config/` with split settings under `config/settings/`. Django apps are under `apps/`: `accounts`, `administration`, `dashboard`, and `messaging`. Each app keeps its own Python modules, migrations, templates, and static assets; shared templates and static assets are in root-level `templates/` and `static/`.
- **Views and URLs:** Views are predominantly function-based. App URL modules use named `path()` routes. `dashboard` is explicitly namespaced; `administration` and `messaging` declare `app_name`; account route names are unnamespaced.
- **Models and queries:** Models use Django ORM fields, relationships with `related_name`, `TextChoices`, and model `Meta` options such as ordering, constraints, and indexes. Views and app service/selector modules use QuerySets, `get_object_or_404()`, and relationship-loading methods such as `select_related()`.
- **Forms:** Django `Form` and `ModelForm` classes handle input and validation, including `clean_<field>()` and `clean()` methods. Views validate bound forms and handle uploaded files through `request.FILES`.
- **Templates:** `templates/base.html` is the shared base; app templates generally extend it and fill blocks. Administration has `administration/base_admin.html` as an intermediate base. Templates use component and partial includes. Template filenames use both hyphens and underscores.
- **Static files and JS/backend communication:** Shared CSS and JavaScript live in root `static/css/` and `static/js/`; app assets live under each app's `static/`, commonly split into `css/` and `js/` and sometimes feature subfolders. Filenames are mostly kebab-case. JavaScript uses `fetch()` or `XMLHttpRequest` for AJAX requests, usually with `X-Requested-With`; Django endpoints return `JsonResponse` for asynchronous operations, while ordinary form posts commonly redirect and use messages. Messaging centralizes request helpers in `messaging/static/messaging/js/api.js`. Templates pass route URLs to scripts through rendered URLs and `data-*` attributes.
- **Naming and indentation:** Python modules, functions, and fields use snake_case; classes use PascalCase. JavaScript identifiers use camelCase. Four-space indentation is common, but `dashboard/models.py` uses tabs.

# Permanent Instructions

1. Study before coding. Read the relevant parts of the project first and find a similar existing feature to mirror before implementing anything.
2. Follow the existing style. Do not invent your own. Do not introduce new libraries, patterns, or architecture unless I explicitly ask. Do not refactor, rename, or restyle existing code unless I ask.
3. Use real Django, not just HTML/CSS/JS. Wire every feature through models, migrations, views, urls, forms, and templates the way the project already does. Use {% url %}, {% static %}, {% csrf_token %}, and template inheritance consistently with the rest of the project. No frontend-only solutions where Django logic is needed.
4. Write clean, concise code. Avoid unnecessary comments. Only comment where the logic is genuinely not obvious.
5. For every new feature, create new HTML, CSS, and JS files instead of adding to existing ones, so features are easy to find and fix. Place them in the same folders and follow the same naming style the project already uses. Only edit existing files when integration requires it (urls, base template links, navigation).
6. At the end of every coding session, always report: new files created (full paths), existing files modified (full paths with a one-line note on each change), and whether migrations are needed (with the commands to run).
7. If a request is ambiguous or conflicts with the existing patterns, ask me before writing code.
