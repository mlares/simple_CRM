# Spreadsheet import and lineage contract

CRM-010 owns lossless spreadsheet staging in `simple_crm.data_quality`. An
upload stores the source filename, content type, byte size, SHA-256 checksum,
raw workbook bytes, upload actor, parser version, application version, and one
`SourceRecord` for each non-empty source row. Each row retains sheet name,
source coordinate, row number, JSON-safe raw values, row checksum,
classification, errors, warnings, canonical-link payload, and rejection reason.

## State and idempotency

The explicit batch state sequence is `STAGED → VALIDATED → CANDIDATE_MATCHED →
APPROVED → APPLYING → APPLIED → RECONCILED`; `FAILED` records an unsuccessful
boundary. The current parser creates `STAGED` batches and records preview
counts for errors, warnings, duplicates, unmatched rows, and canonical diffs.
Checksum plus parser version plus application version is unique, so rerunning
the same workbook/version returns the existing preview and creates no duplicate
source document, batch, or row.

Only `.xlsx` files up to 10 MB are accepted. Unexpected headers, unreadable
workbooks, empty content, and oversized files fail with a Spanish validation
message before staging writes. Excel error cells are retained as raw values and
classified as row errors; ambiguous values are not auto-corrected.

## Approval, application, and lineage

Upload, approval, and application are separate immutable audit events. Only an
enabled `data_steward` or `system_administrator` with global import scope can
preview, approve, or apply a batch; approval and application require explicit
reasons. Applying a batch commits the approved staged state atomically and marks
rows applied without guessing canonical entities. Canonical creation or
correction belongs to the governed CRM-011/CRM-021 workflow, where each
`SourceCanonicalLink` can preserve target type, target identifier, relation,
and evidence.

No workbook data is loaded automatically into production, and direct database
editing during migration is out of scope.
