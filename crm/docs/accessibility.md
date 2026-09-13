# Accessible Spanish-first experience

CRM-018 keeps the critical pages server-rendered and usable with ordinary
links and forms. Every page declares Spanish (`es-AR`), a viewport and
description, provides a keyboard-visible skip link, and loads the local
accessibility stylesheet. Focus is never conveyed only by color: controls use a
visible `:focus-visible` outline and touch-capable controls have a 44-pixel
class minimum height.

The page order is intentionally simple: navigation, a skip link target named
“contenido”, a single page heading, labeled controls, status/error text, and
responsive cards or controlled table overflow. Search and report result
counts use live status text. Empty states explain what to do next. Bootstrap is
vendored locally and HTMX is optional; no template relies on an `hx-*`
attribute for ordinary navigation or submission.

The public `/ayuda/` page is the maintained “Cómo trabajamos” guide. It links
to Today, search and segments, and includes the glossary for lead, stage, task,
view and scope. Quality guidance explicitly keeps clinical and patient data
out of this commercial CRM.

Manual release checks remain required for keyboard traversal from Today to a
lead and contact workflow, 200% zoom, a common phone viewport, and a screen
reader. Automated contract checks cover document language/metadata, skip-link
and focus hooks, native form methods/labels, no-JavaScript attributes, and
the public guide.
