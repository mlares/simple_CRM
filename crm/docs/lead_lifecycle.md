# Lead lifecycle contract

CRM-007 keeps a lead separate from the reusable `Party` master record. A lead
belongs to one campaign and may link organizations or people through explicit
`ACCOUNT`, `PRIMARY_CONTACT`, `SECONDARY_CONTACT`, `SECRETARY`, or `OTHER`
roles. The link is the campaign relationship; it does not copy identity data.

Each lead has a stable human-readable number, current stage, data-readiness
state, source attribution, lifecycle state, timestamps, and an optimistic
`version`. Archiving is the non-destructive end state. Leads are not deleted.

## Stages and history

The baseline stage policy accepts `NUEVO → EN_GESTION → CERRADO`, with a direct
`NUEVO → CERRADO` path. Stage changes must go through
`simple_crm.crm.lead_services.transition_lead()`. The service locks the lead,
checks the caller's campaign/team scope and expected version, validates the
transition and reason, validates required fields, updates the current stage,
and appends one immutable `LeadStageHistory` row in the same transaction.

`LeadStageHistory` records the previous and new stage, occurrence time, actor,
reason, and JSON-safe stage-specific fields. Existing history cannot be edited
or deleted. The initial `NUEVO` entry is written atomically with lead creation,
so the current stage always has a corresponding accepted history entry.

An in-progress lead must carry either a task description and due time or an
explicit documented reason. A close additionally requires `closure_reason`.
CRM-008 may later replace the compact next-action commitment with first-class
tasks while preserving this transition boundary.

## Ownership and visibility

`LeadAssignment` is an append-only operational history. An active lead may have
only one active assignment for each assignment role, including one primary
owner. Reassignment closes the previous primary row and creates a new row in
one transaction; it never overwrites ownership history.

Visibility and mutations use the CRM-005 identity policy. Campaign and team
scopes are checked for the requested action, and list queries must use
`visible_leads()`/`scoped_queryset()` rather than trusting URL or request-body
identifiers. An enabled replacement owner must also have view scope for the
lead's campaign/team.

## Creation and duplicate warnings

`create_lead()` validates the creator and owner, previews existing active leads
for the same campaign and linked party, and returns warnings without merging or
discarding the new candidate. It then writes the lead, party links, primary
owner, source attribution, next-action commitment, and initial stage history
under one transaction. A failed validation rolls back the complete operation.
