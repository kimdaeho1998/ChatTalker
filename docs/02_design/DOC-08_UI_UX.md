# DOC-08 UI/UX Screen Specification

| Screen | Core behavior / states | Contract |
|---|---|---|
| Login / forced change | Credentials; forced-change form; invalid, disabled, offline states | AUTH-001–003 |
| Conversation list / chat | 1:1/group selection, messages, explicit read, reconnect indicator, source links | MSG-001–006 |
| Group management | Membership shown only to eligible users; confirmation/error | MSG-002 |
| Search / attachments | Scoped search; private-R2 attachment pending/scan-failed/available states; empty/error state | MSG-005,007, ATT-001 |
| Morning briefing | First activation prompt/card; ranked source-linked items; raw-unread fallback; does not alter unread badges | AI-001–005 |
| My tasks / calendar | Create, check, completion time, carryover lineage, recurring task labels, holiday/no-calendar warning | TASK-001–005 |
| Task metrics / admin | Personal metrics; authorized administrators choose only allowed scopes; forbidden state | TASK-006–007 |
| Tray / notifications / settings | Notification deep link, tray status, auto-start and signature-verification failure states | MSG-008, WIN-001 through WIN-003 |

Keyboard focus, labels, visible failure recovery, and local date/time display are required. UI never claims send/read/complete success until server confirmation. Windows settings behavior remains contingent on ADR-008.
