# Today workspace contract

CRM-009 owns the server-rendered seller workspace in `simple_crm.platform`.
The `/today/` page requires an authenticated enabled identity and builds its
cards only from `visible_leads()` plus scope-authorized activity queries. The
`/leads/<lead-number>/` detail route uses the human-readable lead number and
returns no result for an inaccessible object; a raw primary key does not grant
access.

## Navigation and urgency

The main navigation exposes Hoy, Mis leads, Buscar, Informes, Calidad de datos,
and Ayuda. Features not yet implemented are visibly disabled rather than
pointing to misleading or unsafe endpoints. Today cards use a fixed ordering:

1. overdue open or rescheduled tasks;
2. tasks due on the team-local current date;
3. inbound responses from the recent response window;
4. in-progress leads without movement for the stale threshold; and
5. unassigned leads, visible to identities authorized to reassign.

Every card links to the relevant lead detail view. Empty work renders a plain
Spanish state that explains the seller has nothing urgent to do. The detail
page combines parties, stage, readiness, source summary, owner, timeline, and
tasks while hiding table names, foreign keys, SQL vocabulary, and raw IDs.

The workspace is presentation-only: lead, interaction, task, stage, and
assignment writes remain in CRM-007 and CRM-008 service boundaries.
