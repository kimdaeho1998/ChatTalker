# DOC-06 Database Design

## Core relational contract
`accounts(id, login unique, status, auth_version, department_id, role_id, created_at)`; `sessions(id, account_id, auth_version, revoked_at, expires_at)`; `audit_events(id, actor_id, action, target_type, target_id, before_json, after_json, created_at)`.

`conversations(id, kind, created_at)`; `conversation_members(conversation_id, account_id, joined_at, left_at, role)`; `messages(id, conversation_id, sender_id, body, created_at, client_idempotency_key, unique(sender_id,client_idempotency_key))`; `message_reads(message_id, account_id, read_at, primary key(message_id,account_id))`; `delivery_events(cursor bigint primary key, account_id, event_type, entity_id, created_at)`. Attachments reference message and storage object only after ADR-005.

`briefing_runs(id, account_id, local_date, message_range_hash, prompt_version, status, response_json, expires_at, unique(account_id,local_date,message_range_hash,prompt_version))`. Response contains message IDs, not independent authority; each retrieval rechecks membership.

`tasks(id, root_task_id nullable, assignee_id, title, planned_date, due_at nullable, origin_created_at, state, completed_at, carried_from_task_id nullable, recurrence_rule_id nullable, created_at)`; `task_check_events(id, task_id, actor_id, old_state, new_state, occurred_at)`; `recurrence_rules(id, assignee_id, weekdays, active)`; `task_instances(recurrence_rule_id, scheduled_date, task_id, unique(recurrence_rule_id,scheduled_date))`; `business_calendar(calendar_date primary key, is_business_day, source, revision)`; `admin_scopes(admin_id, department_id)`.

## Invariants and transactions
All foreign keys enforce ownership. Account disable changes `auth_version` and revokes sessions in one transaction. Message acknowledgement follows commit. Carryover creates linked task with same root and origin date in a transaction; source task remains historically accurate. Recurrence insert uses the unique instance constraint. Metrics use completed check events/tasks, not AI output. UTC persistence; display timezone conversion is client/user-profile aware. Retention, backups, encryption-at-rest and attachment storage are pending approved operations policy.

## R2 contract additions
Add `attachments(id, message_id, object_key, scan_status, scanned_at, created_at)`; no public R2 URL is stored, and `scan_status=passed` is mandatory for retrieval. `business_calendar.source` is one of `korean_public_holiday`, `admin_day_off`, or `working_day`; revisions preserve calendar provenance. `briefing_runs` is built only from unread messages in requester-accessible work conversations. Account credentials use Argon2id-derived verifier material; session expiry value remains externally approved configuration. Audit records include administrator scope-sensitive changes and queries.
