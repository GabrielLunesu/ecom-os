# Ecom-OS — Slice 4: Tasks (per-person Kanban)

Build Spec §7.3 (reshape boards/tasks into a per-person Kanban for the team).

## What shipped
- `team_tasks` table (migration c6d7e8f9a0b1): title, assignee, status (todo/doing/done).
- Service: seed + list + create + update; API GET/POST /ecom/tasks, PATCH /ecom/tasks/{id}.
- Tasks page: three lanes with drag-and-drop (HTML5 DnD + Framer layout for smooth
  reflow), assignee avatar chips, and an add-task form. Optimistic via react-query.

## Verify
- Browser: lanes render with seeded tasks + assignee avatars; add + drag wired.
  mypy clean; tsc 0 errors.
