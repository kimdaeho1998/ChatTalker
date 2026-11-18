# DOC-04 Non-Functional Requirements

| ID / priority | Constraint and acceptance criterion |
|---|---|
| NFR-001 P0 Security | TLS for API/WebSocket, secure credential hashing, least privilege, and server-side authorization. Security test rejects plaintext transport and privilege escalation. |
| NFR-002 P0 Availability | Durable message acknowledgement precedes success; reconnect/sync restores authorized missed events. Fault test meets MSG-004. |
| NFR-003 P0 Integrity | Transactions, foreign keys, idempotency keys and uniqueness constraints prevent orphan/duplicate message and task automation records. Constraint tests pass. |
| NFR-004 P1 Performance | Initial target is 50 concurrent authenticated users and persisted-message delivery p95 <=1 second under an Owner-approved load fixture. Test parameters/production SLO remain OPEN; no performance PASS without measured evidence. |
| NFR-005 P0 Observability | Structured logs, metrics and auditable security changes omit secrets/message bodies unless approved. Failure paths expose correlation ID. |
| NFR-006 P0 Privacy | AI data minimization, access isolation, retention/deletion and provider terms require Owner approval. No AI invocation before ADR-007 approval. |
| NFR-007 P1 Usability | Windows UI supports keyboard navigation, clear unread/briefing fallback state, and readable error recovery. Accessibility review has no blocker. |
| NFR-008 P0 Operability | Dependencies/versions are verified in R01; independent backend/DB has backup, migration and rollback plan before release. |
| NFR-009 P0 Compatibility | Support Windows 10/11 and approved Tauri 2 supported runtime combinations; compatibility matrix is verified in R01. |
| NFR-010 P0 Change safety | No push/deploy/production mutation without Owner approval; release checklist and test evidence required. |
