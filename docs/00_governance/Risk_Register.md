# Risk Register

| Risk ID | Risk / trigger | Impact | Mitigation / owner | Status |
|---|---|---|---|---|
| RISK-001 | Holiday/calendar authority not chosen | Incorrect carryover or recurrence date | ADR-004; scheduler fails safe; Owner | Open |
| RISK-002 | AI provider/data terms unapproved | Privacy/compliance breach or blocked briefing | ADR-007; no outbound AI call; Owner/Security | Open |
| RISK-003 | File storage/scanning policy absent | Malware, data leakage, retention failure | ADR-005; no attachment implementation; Owner/Security | Open |
| RISK-004 | Identity/password/session policy absent | Weak authentication or implementation rework | ADR-006; no production auth configuration; Owner/Security | Open |
| RISK-005 | Department delegation undefined | Excess administrative task visibility | ADR-009; deny by default; Owner | Open |
| RISK-006 | Capacity and recovery objectives undefined | Unverified performance/availability | Define targets, load and restore testing; Owner/Operations | Open |
| RISK-007 | Version/toolchain incompatibility | Windows build/runtime failure | WO-R01-01 compatibility spike before coding; Technical Lead | Open |
| RISK-008 | Unauthorized legacy/production access | Operational outage/data impact | Separate paths/credentials and change controls; all contributors | Controlled |
