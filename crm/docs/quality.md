# Data-quality queue and governed merge contract

CRM-011 owns quality issues, match candidates, review decisions, and
non-destructive merge transactions in `simple_crm.data_quality`. Issues carry a
rule, severity, source/canonical target, owner, state, decision, timestamps,
and acceptance reason. The queue orders errors before warnings before
information, then by age and stable identifier.

Exact email/phone candidates are deterministic and evidence-backed. Fuzzy name
or organization similarity creates only a `REVIEW` candidate with confidence,
algorithm, threshold, and compared names. It never updates a Party, Lead,
Interaction, Task, ContactPoint, or source link by itself. A candidate must be
explicitly approved with a reason before merge.

## Merge preview and application

`preview_merge()` enumerates candidate lead links, interaction participants,
tasks, contact links, aliases, and source-canonical links. The preview is the
review surface; conflicts are rejected rather than silently discarded.

`merge_approved_candidate()` locks both parties and applies the approved merge
in one transaction. It redirects non-conflicting lead and activity links,
shares contact-point links without changing suppression, preserves aliases and
source lineage, archives the duplicate instead of deleting it, and writes
before/after/source evidence to an immutable quality audit event. The survivor
and old archived party identifiers remain traceable.

All quality operations require an enabled data steward or system administrator
with global quality scope and a nonblank reason for state-changing decisions.
