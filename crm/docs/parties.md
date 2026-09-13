# Party master-data contract

CRM-006 owns reusable commercial identities. A `Party` is exactly one
`Person` or `Organization` subtype, enforced by the database check constraint;
the subtype tables contain only subtype attributes. A person may have many
effective-dated `OrganizationPerson` relationships with role and area titles.
The model does not contain patient, specimen, pathology, or other clinical
identity data.

## Contact points and provenance

`ContactPoint` stores one atomic email, phone, WhatsApp, website, or social
value. `PartyContactPoint` links it to one or more parties, which allows a
shared institutional switchboard or secretariat value without treating it as a
personal identifier. The raw value and provenance JSON remain unchanged;
normalization writes a separate comparison value and explicit quality state.

Emails are trimmed and case-folded. Argentinian phone values are parsed to E.164
only when valid and unambiguous. Invalid or incomplete values retain their raw
text and receive `INVALID` or `AMBIGUOUS`. Exact email/phone matches and
plausible name matches are returned by `preview_party_creation()` as warnings;
the service never merges records automatically.

Suppression is durable. A suppressed contact point cannot be reactivated by the
normal edit path and is excluded by `ContactPoint.selectable_for_outreach()`.
The contact point may still be retained for historical evidence and linked to
multiple parties.

## Lifecycle and edits

Parties are archived, never deleted. Archive keeps relationships, contact
points, aliases, specialties, addresses, and provenance while
`Party.objects.active()` removes the party from default active lists. Party
updates use a monotonically increasing `version`; saving a stale instance
raises `PartyConcurrencyError` with a readable Spanish message.
