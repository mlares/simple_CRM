from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from simple_crm.activity.models import InteractionDirection, InteractionResult
from simple_crm.activity.services import quick_contact
from simple_crm.crm.lead_services import create_lead
from simple_crm.crm.models import (
    Campaign,
    LeadParty,
    LeadPartyRole,
    PartyAlias,
    PartyContactPoint,
    PartyLifecycle,
)
from simple_crm.crm.services import ContactInput, create_organization_party
from simple_crm.data_quality.models import (
    CandidateMatch,
    ImportBatch,
    ImportStatus,
    MatchState,
    MatchType,
    QualityAuditEvent,
    QualityIssueState,
    QualitySeverity,
    SourceCanonicalLink,
    SourceDocument,
    SourceRecord,
)
from simple_crm.data_quality.services import (
    change_issue_state,
    create_quality_issue,
    find_exact_candidates,
    find_fuzzy_candidate,
    merge_approved_candidate,
    preview_merge,
    quality_issue_queue,
    review_candidate,
)
from simple_crm.identity.models import (
    IdentityProfile,
    Role,
    RoleAssignment,
    ScopeGrant,
    ScopeType,
)


def _actor(username: str, role_code: str = "data_steward") -> IdentityProfile:
    user = get_user_model().objects.create_user(username=username, password="safe-pass")
    profile = IdentityProfile.objects.get(user=user)
    RoleAssignment.objects.create(
        identity=profile, role=Role.objects.get(code=role_code)
    )
    ScopeGrant.objects.create(identity=profile, scope_type=ScopeType.GLOBAL)
    return profile


def _seller(username: str) -> IdentityProfile:
    user = get_user_model().objects.create_user(username=username, password="safe-pass")
    profile = IdentityProfile.objects.get(user=user)
    RoleAssignment.objects.create(
        identity=profile, role=Role.objects.get(code="sales_representative")
    )
    campaign = Campaign.objects.get(code="GENERAL")
    ScopeGrant.objects.create(
        identity=profile, scope_type=ScopeType.CAMPAIGN, campaign=campaign
    )
    return profile


@pytest.mark.django_db
def test_quality_queue_is_prioritized_and_state_transitions_are_audited() -> None:
    steward = _actor("quality-queue")
    error = create_quality_issue(
        actor=steward, rule_code="MISSING_EMAIL", severity=QualitySeverity.ERROR
    )
    warning = create_quality_issue(
        actor=steward, rule_code="POSSIBLE_DUPLICATE", severity=QualitySeverity.WARNING
    )
    info = create_quality_issue(
        actor=steward, rule_code="SOURCE_NOTE", severity=QualitySeverity.INFO
    )

    assert list(quality_issue_queue(steward).values_list("pk", flat=True)) == [
        error.pk,
        warning.pk,
        info.pk,
    ]
    resolved = change_issue_state(
        actor=steward,
        issue=error,
        state=QualityIssueState.RESOLVED,
        reason="Se completó la investigación",
        decision="CORRECTED",
    )
    accepted = change_issue_state(
        actor=steward,
        issue=warning,
        state=QualityIssueState.ACCEPTED,
        reason="El responsable confirma que no se puede resolver ahora",
        decision="ACCEPTED_WARNING",
    )
    assert resolved.resolved_at is not None
    assert accepted.acceptance_reason
    reopened = change_issue_state(
        actor=steward,
        issue=accepted,
        state=QualityIssueState.REOPENED,
        reason="Apareció nueva evidencia",
    )
    assert reopened.state == QualityIssueState.REOPENED
    assert QualityAuditEvent.objects.filter(action="issue_state_changed").count() == 3


@pytest.mark.django_db
def test_exact_and_fuzzy_candidates_are_review_only_until_approved() -> None:
    steward = _actor("quality-match")
    first, _ = create_organization_party(
        display_name="Hospital Central",
        contact_inputs=(ContactInput(kind="EMAIL", raw_value="contacto@test.com"),),
    )
    second, _ = create_organization_party(
        display_name="Hospital Central Sur",
        contact_inputs=(ContactInput(kind="EMAIL", raw_value="contacto@test.com"),),
    )

    exact = find_exact_candidates(
        actor=steward, kind="EMAIL", normalized_value="contacto@test.com"
    )
    assert len(exact) == 1
    assert exact[0].match_type == MatchType.EXACT_EMAIL
    fuzzy = find_fuzzy_candidate(actor=steward, first=first, second=second)
    assert fuzzy.state == MatchState.REVIEW
    assert CandidateMatch.objects.filter(state=MatchState.REVIEW).exists()
    with pytest.raises(ValidationError, match="aprobarse"):
        merge_approved_candidate(
            actor=steward, candidate=fuzzy, reason="Intento automático"
        )
    assert first.lifecycle == PartyLifecycle.ACTIVE
    assert second.lifecycle == PartyLifecycle.ACTIVE


@pytest.mark.django_db
def test_merge_preview_and_approved_merge_preserve_related_records_and_suppression() -> (
    None
):
    steward = _actor("quality-merge")
    seller = _seller("quality-seller")
    survivor, _ = create_organization_party(display_name="Hospital Madre")
    duplicate, _ = create_organization_party(
        display_name="Hospital Madre (fuente)",
        contact_inputs=(ContactInput(kind="EMAIL", raw_value="suppressed@test"),),
    )
    contact = duplicate.contact_point_links.get().contact_point
    contact.suppress("No contactar")
    PartyAlias.objects.create(
        party=duplicate,
        alias_value="Hospital Madre (fuente)",
        alias_normalized="hospital madre fuente",
    )
    campaign = Campaign.objects.get(code="GENERAL")
    lead, _ = create_lead(
        actor=seller,
        campaign=campaign,
        owner=seller,
        parties=((duplicate, LeadPartyRole.ACCOUNT),),
    )
    quick_contact(
        actor=seller,
        lead=lead,
        occurrence_date=date.today(),
        direction=InteractionDirection.OUTBOUND,
        channel_code="EMAIL",
        outcome_code="CONTACTADO",
        result=InteractionResult.COMPLETED,
        note="Se confirmó la cuenta.",
        participants=(duplicate,),
    )
    document = SourceDocument.objects.create(
        filename="merge.xlsx",
        size_bytes=0,
        checksum="b" * 64,
        content=b"",
        uploaded_by=steward.user,
    )
    batch = ImportBatch.objects.create(
        source_document=document,
        checksum="b" * 64,
        parser_version="test",
        application_version="test",
        status=ImportStatus.STAGED,
        import_actor=steward.user,
    )
    source_record = SourceRecord.objects.create(
        batch=batch,
        sheet_name="Leads",
        row_number=2,
        source_coordinate="Leads!2",
        raw_payload={"organization": duplicate.display_name},
        raw_checksum="a" * 64,
    )
    # The source record foreign key is intentionally exercised through a real
    # imported row in the next test; this preview only needs canonical links.
    SourceCanonicalLink.objects.create(
        source_record=source_record,
        target_type="Party",
        target_id=str(duplicate.pk),
        relation="source_party",
    )
    match = CandidateMatch.objects.create(
        survivor=survivor,
        candidate=duplicate,
        match_type=MatchType.FUZZY_ORGANIZATION,
        confidence="0.9500",
        evidence={"reason": "same organization"},
    )
    review_candidate(
        actor=steward,
        candidate=match,
        state=MatchState.APPROVED,
        reason="El responsable confirmó la coincidencia",
    )
    preview = preview_merge(actor=steward, candidate=match)
    assert lead.pk in {link.lead_id for link in preview.lead_links}
    assert preview.interactions
    assert preview.tasks == ()
    assert preview.contact_links
    assert preview.aliases
    assert preview.source_links

    merged = merge_approved_candidate(
        actor=steward, candidate=match, reason="Fusión aprobada con evidencia"
    )
    duplicate.refresh_from_db()
    assert merged.pk == survivor.pk
    assert duplicate.lifecycle == PartyLifecycle.ARCHIVED
    assert LeadParty.objects.get(lead=lead).party_id == survivor.pk
    assert lead.interactions.first().participants.get().party_id == survivor.pk
    assert PartyContactPoint.objects.filter(
        party=survivor, contact_point=contact
    ).exists()
    assert contact.is_suppressed is True
    assert PartyAlias.objects.filter(party=survivor, alias_type="MERGED_FROM").exists()
    assert SourceCanonicalLink.objects.filter(
        source_record=source_record, target_id=str(survivor.pk)
    ).exists()
    assert QualityAuditEvent.objects.filter(action="party_merged").exists()
