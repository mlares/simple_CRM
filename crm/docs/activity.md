# Interaction, task, and timeline contract

CRM-008 owns the activity domain in `simple_crm.activity`. An interaction is a
real event linked to one lead, with occurrence date, optional exact time,
direction, governed channel/outcome, contact-result semantics, participants,
note, actor, and source metadata. The occurrence date is never replaced by
the entry timestamp; when the source has no exact time, `occurrence_time`
remains empty.

The quick-contact service is `quick_contact()`. It re-checks the CRM-005
create scope for the locked lead, validates the channel and outcome catalog
values, rejects placeholders such as `Sin acción`, and can write an optional
participant set, next task, and lead-stage transition. The interaction, task,
stage change, and `ActivityAuditEvent` are one transaction. A failure rolls
back all of them.

## Governed contact semantics

`ATTEMPTED`, `COMPLETED`, and `RESPONSE` distinguish an attempt, a completed
contact, and an inbound response. A response must be inbound; an inbound event
must use a channel whose catalog entry allows inbound traffic; `CONTACTADO`
cannot be recorded as only an attempt; and `SIN_RESPUESTA` cannot be recorded
as a completed contact. The CRM outcome catalog remains the source of labels
and follow-up behavior.

## Tasks

A task has a lead, owner, description, due date, state, priority, optional
originating interaction, and completion/reschedule details. Database and model
validation enforce that completed tasks have a completion timestamp, open or
cancelled tasks do not, and reprogrammed tasks have a timestamp and reason.
`complete_task()` and `reschedule_task()` perform scope checks, lock the row,
write the state change, and append an activity audit event. Overdue is computed
against the current team-local date, not a naive UTC conversion.

## Timeline and privacy boundary

`lead_timeline()` returns a stable ordered projection of interactions, stage
history, and assignment history. Each event carries occurrence date/time,
entry time, source label, event type, and its domain record. It re-checks view
scope before loading the lead, so a direct URL or guessed identifier cannot
reveal another campaign's timeline.

## Moderated usability checklist

Once the CRM-009 seller UI calls this boundary, observe a representative seller
perform these steps without database terminology: open an assigned lead, record
today's channel/direction/outcome/note, optionally add the next task, save, and
open the resulting timeline. Record elapsed time, errors, help requests, and
whether the user can distinguish attempted contact, response, next task, and
date-only occurrence. The target is completion in under 60 seconds without
technical assistance; this repository currently provides the domain boundary
and checklist, while the browser session is a staging follow-up.

Call recording and email inbox synchronization are intentionally out of scope.
