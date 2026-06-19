"""A08 metric read tools for A03 catalog registration.

This module does not register tools globally. It exports definitions and handlers so the
A03 tool-catalog owner can generate adapter/MCP registrations from one canonical catalog.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.metrics.brief_generation import (
    DailyBriefFromMetricRequest,
    UnavailableBriefSection,
    generate_daily_brief_detail_from_metric_snapshot,
)
from app.metrics.briefs import (
    DailyBriefItem,
    DailyBriefRequest,
    DailyBriefSection,
    DailyBriefSectionKind,
    ensure_daily_brief_delivery_intent,
    generate_daily_brief_snapshot,
    persist_daily_brief_snapshot,
    record_daily_brief_delivery_result,
    record_daily_brief_narration_result,
)
from app.metrics.formulas import FreshnessStatus, SourceCoverage
from app.metrics.read_models import (
    DailyBriefDetail,
    MetricSnapshotDetail,
    build_metric_explain_context,
    get_daily_brief_delivery_packet,
    get_daily_brief_detail_by_id,
    get_latest_daily_brief_detail,
    get_metric_snapshot_detail,
    get_metric_snapshot_detail_by_id,
    list_daily_brief_delivery_intents,
)

ToolHandler = Callable[[dict[str, Any]], Awaitable["MetricToolResult"]]


class MetricToolDefinition(SQLModel):
    name: str
    version: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    read_or_write: Literal["read", "write"]
    risk_class: str
    required_ecom_permissions: list[str]
    required_connection_types: list[str]
    store_scope_rule: str
    supports_simulation: bool
    supports_idempotency: bool
    reconciliation_strategy: str
    sensitive_fields: list[str]
    minimum_trace_coverage: str


class MetricToolResult(SQLModel):
    ok: bool
    status: str
    trace_id: str | None
    invocation_id: str | None
    action_id: str | None = None
    approval_id: str | None = None
    data: dict[str, Any]
    evidence: list[dict[str, str]]
    freshness: dict[str, str | None]
    warnings: list[str]
    error: dict[str, str] | None


_SNAPSHOT_REF_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "snapshot_id": {"type": "string", "description": "Metric snapshot UUID."},
        "store_id": {"type": "string", "description": "Store ID when requesting latest."},
        "metric_name": {
            "type": "string",
            "default": "estimated_contribution_margin",
        },
        "currency": {"type": "string", "minLength": 3, "maxLength": 3},
    },
    "oneOf": [
        {"required": ["snapshot_id"]},
        {"required": ["store_id"]},
    ],
    "additionalProperties": False,
}

_TOOL_RESULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["ok", "status", "data", "evidence", "freshness", "warnings", "error"],
    "properties": {
        "ok": {"type": "boolean"},
        "status": {"type": "string"},
        "trace_id": {"type": ["string", "null"]},
        "invocation_id": {"type": ["string", "null"]},
        "data": {"type": "object"},
        "evidence": {"type": "array", "items": {"type": "object"}},
        "freshness": {"type": "object"},
        "warnings": {"type": "array", "items": {"type": "string"}},
        "error": {"type": ["object", "null"]},
    },
}


METRIC_TOOL_DEFINITIONS: tuple[MetricToolDefinition, ...] = (
    MetricToolDefinition(
        name="ecom.metric.get",
        version="1.0.0",
        description="Read a deterministic Ecom-OS metric snapshot with components and evidence.",
        input_schema=_SNAPSHOT_REF_SCHEMA,
        output_schema=_TOOL_RESULT_SCHEMA,
        read_or_write="read",
        risk_class="low",
        required_ecom_permissions=["finance:read"],
        required_connection_types=[],
        store_scope_rule="required for latest lookup; snapshot ID is already scoped",
        supports_simulation=False,
        supports_idempotency=True,
        reconciliation_strategy="not_applicable_read_only",
        sensitive_fields=[],
        minimum_trace_coverage="verified",
    ),
    MetricToolDefinition(
        name="ecom.metric.explain",
        version="1.0.0",
        description=(
            "Read a metric explanation context for Hermes narration without recalculating numbers."
        ),
        input_schema={
            "type": "object",
            "required": ["snapshot_id"],
            "properties": {
                "snapshot_id": {"type": "string", "description": "Metric snapshot UUID."}
            },
            "additionalProperties": False,
        },
        output_schema=_TOOL_RESULT_SCHEMA,
        read_or_write="read",
        risk_class="low",
        required_ecom_permissions=["finance:read"],
        required_connection_types=[],
        store_scope_rule="snapshot ID is already scoped",
        supports_simulation=False,
        supports_idempotency=True,
        reconciliation_strategy="not_applicable_read_only",
        sensitive_fields=[],
        minimum_trace_coverage="verified",
    ),
)


_BRIEF_REF_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "brief_id": {"type": "string", "description": "Daily brief UUID."},
        "store_id": {"type": "string", "description": "Store ID when requesting latest."},
        "reporting_date": {"type": "string", "format": "date"},
        "reporting_timezone": {"type": "string"},
    },
    "oneOf": [
        {"required": ["brief_id"]},
        {"required": ["store_id"]},
    ],
    "additionalProperties": False,
}


DAILY_BRIEF_TOOL_DEFINITIONS: tuple[MetricToolDefinition, ...] = (
    MetricToolDefinition(
        name="ecom.daily_brief.get",
        version="1.0.0",
        description="Read a deterministic Ecom-OS daily brief snapshot and delivery status.",
        input_schema=_BRIEF_REF_SCHEMA,
        output_schema=_TOOL_RESULT_SCHEMA,
        read_or_write="read",
        risk_class="low",
        required_ecom_permissions=["brief:read"],
        required_connection_types=[],
        store_scope_rule="required for latest lookup; brief ID is already scoped",
        supports_simulation=False,
        supports_idempotency=True,
        reconciliation_strategy="not_applicable_read_only",
        sensitive_fields=[],
        minimum_trace_coverage="verified",
    ),
    MetricToolDefinition(
        name="ecom.daily_brief.generate",
        version="1.0.0",
        description=(
            "Generate or retrieve an idempotent deterministic daily brief snapshot. "
            "This does not send a channel message."
        ),
        input_schema={
            "type": "object",
            "required": ["brand_id", "store_id", "reporting_date", "reporting_timezone"],
            "properties": {
                "brand_id": {"type": "string"},
                "store_id": {"type": "string"},
                "reporting_date": {"type": "string", "format": "date"},
                "reporting_timezone": {"type": "string"},
                "revision": {"type": "integer", "default": 1},
                "sections": {"type": "array", "items": {"type": "object"}},
                "metric_snapshot_ids": {"type": "array", "items": {"type": "string"}},
                "generated_at": {"type": "string", "format": "date-time"},
                "trace_id": {"type": ["string", "null"]},
            },
            "additionalProperties": False,
        },
        output_schema=_TOOL_RESULT_SCHEMA,
        read_or_write="write",
        risk_class="internal_state",
        required_ecom_permissions=["brief:write"],
        required_connection_types=[],
        store_scope_rule="exact store_id required",
        supports_simulation=False,
        supports_idempotency=True,
        reconciliation_strategy="idempotent_by_brand_store_date_timezone_revision",
        sensitive_fields=[],
        minimum_trace_coverage="verified_after_a02_invocation_record",
    ),
    MetricToolDefinition(
        name="ecom.daily_brief.generate_from_metric",
        version="1.0.0",
        description=(
            "Generate or retrieve an idempotent deterministic daily brief from one exact "
            "metric snapshot. This does not send a channel message."
        ),
        input_schema={
            "type": "object",
            "required": [
                "brand_id",
                "store_id",
                "reporting_date",
                "reporting_timezone",
                "metric_snapshot_id",
            ],
            "properties": {
                "brand_id": {"type": "string"},
                "store_id": {"type": "string"},
                "reporting_date": {"type": "string", "format": "date"},
                "reporting_timezone": {"type": "string"},
                "metric_snapshot_id": {"type": "string"},
                "revision": {"type": "integer", "default": 1},
                "unavailable_sections": {"type": "array", "items": {"type": "object"}},
                "generated_at": {"type": "string", "format": "date-time"},
                "trace_id": {"type": ["string", "null"]},
            },
            "additionalProperties": False,
        },
        output_schema=_TOOL_RESULT_SCHEMA,
        read_or_write="write",
        risk_class="internal_state",
        required_ecom_permissions=["brief:write"],
        required_connection_types=[],
        store_scope_rule="exact store_id and metric_snapshot_id required",
        supports_simulation=False,
        supports_idempotency=True,
        reconciliation_strategy="idempotent_by_brand_store_date_timezone_revision",
        sensitive_fields=[],
        minimum_trace_coverage="verified_after_a02_invocation_record",
    ),
    MetricToolDefinition(
        name="ecom.daily_brief.delivery_intent.ensure",
        version="1.0.0",
        description=(
            "Create or read an idempotent pending Hermes-native delivery intent for a stored "
            "daily brief. This does not call Slack, Telegram, email, or any channel transport."
        ),
        input_schema={
            "type": "object",
            "required": ["brief_id", "target_platform", "target_channel_ref"],
            "properties": {
                "brief_id": {"type": "string"},
                "target_platform": {"type": "string"},
                "target_channel_ref": {"type": "string"},
                "trace_id": {"type": ["string", "null"]},
            },
            "additionalProperties": False,
        },
        output_schema=_TOOL_RESULT_SCHEMA,
        read_or_write="write",
        risk_class="internal_state",
        required_ecom_permissions=["brief:deliver"],
        required_connection_types=[],
        store_scope_rule="brief ID is already scoped",
        supports_simulation=False,
        supports_idempotency=True,
        reconciliation_strategy="idempotent_by_brief_platform_channel",
        sensitive_fields=[],
        minimum_trace_coverage="verified_after_a02_invocation_record",
    ),
    MetricToolDefinition(
        name="ecom.daily_brief.delivery_intent.dispatch_packet.get",
        version="1.0.0",
        description=(
            "Read the A08 dispatch packet for an existing daily brief delivery intent. "
            "This returns body, idempotency key, guardrails, and safe-dispatch status; "
            "it does not send a channel message."
        ),
        input_schema={
            "type": "object",
            "required": ["intent_id"],
            "properties": {
                "intent_id": {"type": "string"},
            },
            "additionalProperties": False,
        },
        output_schema=_TOOL_RESULT_SCHEMA,
        read_or_write="read",
        risk_class="low",
        required_ecom_permissions=["brief:deliver"],
        required_connection_types=[],
        store_scope_rule="delivery intent ID is already scoped",
        supports_simulation=False,
        supports_idempotency=True,
        reconciliation_strategy="not_applicable_read_only",
        sensitive_fields=[],
        minimum_trace_coverage="verified",
    ),
    MetricToolDefinition(
        name="ecom.daily_brief.narration_result.record",
        version="1.0.0",
        description=(
            "Record an optional Hermes narration result for a stored daily brief. "
            "Failed or unavailable narration uses the deterministic fallback body."
        ),
        input_schema={
            "type": "object",
            "required": ["brief_id", "narration_status"],
            "properties": {
                "brief_id": {"type": "string"},
                "narration_status": {
                    "type": "string",
                    "enum": ["completed", "failed", "unavailable", "not_requested"],
                },
                "narrated_text": {"type": ["string", "null"]},
                "hermes_session_id": {"type": ["string", "null"]},
                "hermes_run_id": {"type": ["string", "null"]},
                "hermes_cron_ref": {"type": ["string", "null"]},
                "trace_id": {"type": ["string", "null"]},
                "error": {"type": ["string", "null"]},
            },
            "additionalProperties": False,
        },
        output_schema=_TOOL_RESULT_SCHEMA,
        read_or_write="write",
        risk_class="internal_state",
        required_ecom_permissions=["brief:write"],
        required_connection_types=[],
        store_scope_rule="brief ID is already scoped",
        supports_simulation=False,
        supports_idempotency=True,
        reconciliation_strategy="fallback_text_on_failed_or_unavailable_narration",
        sensitive_fields=[],
        minimum_trace_coverage="verified_after_a02_invocation_record",
    ),
    MetricToolDefinition(
        name="ecom.daily_brief.delivery_result.record",
        version="1.0.0",
        description=(
            "Record a Hermes-native delivery result for an existing daily brief delivery intent. "
            "This records status/evidence only and does not send a channel message."
        ),
        input_schema={
            "type": "object",
            "required": ["intent_id", "status"],
            "properties": {
                "intent_id": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["pending", "delivered", "failed", "outcome_unknown"],
                },
                "delivery_evidence": {"type": "object"},
                "trace_id": {"type": ["string", "null"]},
                "error": {"type": ["string", "null"]},
                "delivered_at": {"type": ["string", "null"], "format": "date-time"},
            },
            "additionalProperties": False,
        },
        output_schema=_TOOL_RESULT_SCHEMA,
        read_or_write="write",
        risk_class="internal_state",
        required_ecom_permissions=["brief:deliver"],
        required_connection_types=[],
        store_scope_rule="delivery intent ID is already scoped",
        supports_simulation=False,
        supports_idempotency=False,
        reconciliation_strategy="status_callback_records_attempt_and_evidence",
        sensitive_fields=[],
        minimum_trace_coverage="verified_after_a02_invocation_record",
    ),
)


def metric_tool_handlers(session: AsyncSession) -> dict[str, ToolHandler]:
    async def metric_get(arguments: dict[str, Any]) -> MetricToolResult:
        snapshot = await _resolve_snapshot(session, arguments)
        if snapshot is None:
            return _not_found_result()
        return _completed_result(
            data=snapshot.model_dump(mode="json"),
            snapshot=snapshot,
        )

    async def metric_explain(arguments: dict[str, Any]) -> MetricToolResult:
        snapshot_id = str(arguments.get("snapshot_id", "")).strip()
        if not snapshot_id:
            return _not_found_result()
        try:
            context = await build_metric_explain_context(session, snapshot_id=snapshot_id)
        except ValueError:
            context = None
        if context is None:
            return _not_found_result()
        return _completed_result(
            data=context.model_dump(mode="json"),
            snapshot=context.snapshot,
        )

    return {
        "ecom.metric.get": metric_get,
        "ecom.metric.explain": metric_explain,
    }


def daily_brief_tool_handlers(session: AsyncSession) -> dict[str, ToolHandler]:
    async def daily_brief_get(arguments: dict[str, Any]) -> MetricToolResult:
        brief = await _resolve_brief(session, arguments)
        if brief is None:
            return _brief_not_found_result()
        return _completed_brief_result(data=brief.model_dump(mode="json"), brief=brief)

    async def daily_brief_generate(arguments: dict[str, Any]) -> MetricToolResult:
        try:
            snapshot = generate_daily_brief_snapshot(
                DailyBriefRequest(
                    brand_id=str(arguments["brand_id"]),
                    store_id=str(arguments["store_id"]),
                    reporting_date=date.fromisoformat(str(arguments["reporting_date"])),
                    reporting_timezone=str(arguments["reporting_timezone"]),
                    revision=int(arguments.get("revision") or 1),
                ),
                sections=_sections_from_arguments(arguments.get("sections")),
                metric_snapshot_ids=_strings_from_arguments(arguments.get("metric_snapshot_ids")),
                generated_at=_optional_datetime(arguments.get("generated_at")),
                trace_id=_optional_string(arguments.get("trace_id")),
            )
            record = await persist_daily_brief_snapshot(
                session,
                brand_id=UUID(str(arguments["brand_id"])),
                snapshot=snapshot,
            )
            brief = await get_daily_brief_detail_by_id(session, brief_id=str(record.id))
        except (KeyError, TypeError, ValueError):
            brief = None
        if brief is None:
            return _invalid_brief_result()
        return _completed_brief_result(data=brief.model_dump(mode="json"), brief=brief)

    async def delivery_intent_ensure(arguments: dict[str, Any]) -> MetricToolResult:
        brief_id = str(arguments.get("brief_id", "")).strip()
        try:
            brief = await get_daily_brief_detail_by_id(session, brief_id=brief_id)
        except ValueError:
            brief = None
        if brief is None:
            return _brief_not_found_result()
        target_platform = str(arguments.get("target_platform", "")).strip()
        target_channel_ref = str(arguments.get("target_channel_ref", "")).strip()
        if not target_platform or not target_channel_ref:
            return _invalid_brief_result()
        intent = await ensure_daily_brief_delivery_intent(
            session,
            brief_id=UUID(brief_id),
            target_platform=target_platform,
            target_channel_ref=target_channel_ref,
            body_text=brief.final_text or brief.deterministic_fallback_text,
            trace_id=_optional_string(arguments.get("trace_id")),
        )
        intents = await list_daily_brief_delivery_intents(session, brief_id=brief_id)
        intent_data = next(
            (
                read_intent.model_dump(mode="json")
                for read_intent in intents
                if read_intent.id == str(intent.id)
            ),
            {},
        )
        return _completed_brief_result(
            data={"brief": brief.model_dump(mode="json"), "delivery_intent": intent_data},
            brief=brief,
        )

    async def daily_brief_generate_from_metric(arguments: dict[str, Any]) -> MetricToolResult:
        try:
            brief = await generate_daily_brief_detail_from_metric_snapshot(
                session,
                DailyBriefFromMetricRequest(
                    brand_id=UUID(str(arguments["brand_id"])),
                    store_id=str(arguments["store_id"]),
                    reporting_date=date.fromisoformat(str(arguments["reporting_date"])),
                    reporting_timezone=str(arguments["reporting_timezone"]),
                    metric_snapshot_id=str(arguments["metric_snapshot_id"]),
                    revision=int(arguments.get("revision") or 1),
                    unavailable_sections=tuple(
                        _unavailable_sections_from_arguments(arguments.get("unavailable_sections"))
                    ),
                    generated_at=_optional_datetime(arguments.get("generated_at")),
                    trace_id=_optional_string(arguments.get("trace_id")),
                ),
            )
        except (KeyError, TypeError, ValueError):
            brief = None
        if brief is None:
            return _invalid_brief_result()
        return _completed_brief_result(data=brief.model_dump(mode="json"), brief=brief)

    async def narration_result_record(arguments: dict[str, Any]) -> MetricToolResult:
        brief_id = str(arguments.get("brief_id", "")).strip()
        try:
            record = await record_daily_brief_narration_result(
                session,
                brief_id=UUID(brief_id),
                narration_status=str(arguments.get("narration_status", "")),
                narrated_text=_optional_string(arguments.get("narrated_text")),
                hermes_session_id=_optional_string(arguments.get("hermes_session_id")),
                hermes_run_id=_optional_string(arguments.get("hermes_run_id")),
                hermes_cron_ref=_optional_string(arguments.get("hermes_cron_ref")),
                trace_id=_optional_string(arguments.get("trace_id")),
                error=_optional_string(arguments.get("error")),
            )
            brief = (
                await get_daily_brief_detail_by_id(session, brief_id=str(record.id))
                if record is not None
                else None
            )
        except (TypeError, ValueError):
            brief = None
        if brief is None:
            return _invalid_brief_result()
        return _completed_brief_result(data=brief.model_dump(mode="json"), brief=brief)

    async def delivery_dispatch_packet_get(arguments: dict[str, Any]) -> MetricToolResult:
        intent_id = str(arguments.get("intent_id", "")).strip()
        try:
            packet = await get_daily_brief_delivery_packet(session, intent_id=intent_id)
        except (TypeError, ValueError):
            packet = None
        if packet is None:
            return _brief_not_found_result()
        return MetricToolResult(
            ok=True,
            status="completed",
            trace_id=packet.trace_id,
            invocation_id=None,
            data=packet.model_dump(mode="json"),
            evidence=list(packet.evidence),
            freshness={
                "as_of": packet.intent.updated_at.isoformat(),
                "status": packet.dispatch_status,
            },
            warnings=list(packet.warnings),
            error=None,
        )

    async def delivery_result_record(arguments: dict[str, Any]) -> MetricToolResult:
        intent_id = str(arguments.get("intent_id", "")).strip()
        try:
            intent = await record_daily_brief_delivery_result(
                session,
                intent_id=UUID(intent_id),
                status=str(arguments.get("status", "")),
                delivery_evidence=_dict_from_arguments(arguments.get("delivery_evidence")),
                trace_id=_optional_string(arguments.get("trace_id")),
                error=_optional_string(arguments.get("error")),
                delivered_at=_optional_datetime(arguments.get("delivered_at")),
            )
            brief = (
                await get_daily_brief_detail_by_id(session, brief_id=str(intent.brief_id))
                if intent is not None
                else None
            )
        except (TypeError, ValueError):
            brief = None
            intent = None
        if brief is None or intent is None:
            return _invalid_brief_result()
        intents = await list_daily_brief_delivery_intents(session, brief_id=str(intent.brief_id))
        intent_data = next(
            (
                read_intent.model_dump(mode="json")
                for read_intent in intents
                if read_intent.id == str(intent.id)
            ),
            {},
        )
        return _completed_brief_result(
            data={"brief": brief.model_dump(mode="json"), "delivery_intent": intent_data},
            brief=brief,
        )

    return {
        "ecom.daily_brief.get": daily_brief_get,
        "ecom.daily_brief.generate": daily_brief_generate,
        "ecom.daily_brief.generate_from_metric": daily_brief_generate_from_metric,
        "ecom.daily_brief.delivery_intent.ensure": delivery_intent_ensure,
        "ecom.daily_brief.delivery_intent.dispatch_packet.get": delivery_dispatch_packet_get,
        "ecom.daily_brief.narration_result.record": narration_result_record,
        "ecom.daily_brief.delivery_result.record": delivery_result_record,
    }


async def _resolve_snapshot(
    session: AsyncSession,
    arguments: dict[str, Any],
) -> MetricSnapshotDetail | None:
    snapshot_id = str(arguments.get("snapshot_id", "")).strip()
    if snapshot_id:
        try:
            return await get_metric_snapshot_detail_by_id(session, snapshot_id=snapshot_id)
        except ValueError:
            return None

    store_id = str(arguments.get("store_id", "")).strip()
    if not store_id:
        return None
    metric_name = str(arguments.get("metric_name") or "estimated_contribution_margin")
    currency = arguments.get("currency")
    return await get_metric_snapshot_detail(
        session,
        store_id=store_id,
        metric_name=metric_name,
        currency=str(currency) if currency else None,
    )


async def _resolve_brief(
    session: AsyncSession,
    arguments: dict[str, Any],
) -> DailyBriefDetail | None:
    brief_id = str(arguments.get("brief_id", "")).strip()
    if brief_id:
        try:
            return await get_daily_brief_detail_by_id(session, brief_id=brief_id)
        except ValueError:
            return None

    store_id = str(arguments.get("store_id", "")).strip()
    if not store_id:
        return None
    reporting_date = arguments.get("reporting_date")
    return await get_latest_daily_brief_detail(
        session,
        store_id=store_id,
        reporting_date=date.fromisoformat(str(reporting_date)) if reporting_date else None,
        reporting_timezone=_optional_string(arguments.get("reporting_timezone")),
    )


def _completed_result(
    *,
    data: dict[str, Any],
    snapshot: MetricSnapshotDetail,
) -> MetricToolResult:
    return MetricToolResult(
        ok=True,
        status="completed",
        trace_id=snapshot.trace_id,
        invocation_id=None,
        data=data,
        evidence=_evidence_refs(snapshot),
        freshness={
            "as_of": snapshot.finalized_at.isoformat(),
            "status": snapshot.coverage.freshness,
        },
        warnings=list(snapshot.coverage.warnings),
        error=None,
    )


def _completed_brief_result(
    *,
    data: dict[str, Any],
    brief: DailyBriefDetail,
) -> MetricToolResult:
    return MetricToolResult(
        ok=True,
        status="completed",
        trace_id=brief.trace_id,
        invocation_id=None,
        data=data,
        evidence=_brief_evidence_refs(brief),
        freshness={
            "as_of": brief.finalized_at.isoformat(),
            "status": brief.coverage.freshness,
        },
        warnings=list(brief.coverage.warnings),
        error=None,
    )


def _not_found_result() -> MetricToolResult:
    return MetricToolResult(
        ok=False,
        status="failed",
        trace_id=None,
        invocation_id=None,
        data={},
        evidence=[],
        freshness={"as_of": None, "status": "unknown"},
        warnings=[],
        error={
            "code": "metric_snapshot_not_found",
            "message": "metric snapshot not found",
        },
    )


def _brief_not_found_result() -> MetricToolResult:
    return MetricToolResult(
        ok=False,
        status="failed",
        trace_id=None,
        invocation_id=None,
        data={},
        evidence=[],
        freshness={"as_of": None, "status": "unknown"},
        warnings=[],
        error={
            "code": "daily_brief_not_found",
            "message": "daily brief not found",
        },
    )


def _invalid_brief_result() -> MetricToolResult:
    return MetricToolResult(
        ok=False,
        status="failed",
        trace_id=None,
        invocation_id=None,
        data={},
        evidence=[],
        freshness={"as_of": None, "status": "unknown"},
        warnings=[],
        error={
            "code": "daily_brief_invalid_arguments",
            "message": "daily brief arguments are invalid",
        },
    )


def _evidence_refs(snapshot: MetricSnapshotDetail) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    for component in snapshot.components:
        for evidence_ref in component.evidence_refs:
            evidence.append({"type": "metric_component", "id": evidence_ref})
    return evidence


def _brief_evidence_refs(brief: DailyBriefDetail) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    for metric_snapshot_id in brief.metric_snapshot_ids:
        evidence.append({"type": "metric_snapshot", "id": metric_snapshot_id})
    for section in brief.sections:
        for evidence_ref in section.evidence_refs:
            evidence.append({"type": "daily_brief_section", "id": evidence_ref})
        for item in section.items:
            refs = item.get("evidence_refs")
            if isinstance(refs, list):
                for evidence_ref in refs:
                    evidence.append({"type": "daily_brief_item", "id": str(evidence_ref)})
    return evidence


def _sections_from_arguments(value: object) -> list[DailyBriefSection]:
    if not isinstance(value, list):
        return []
    sections: list[DailyBriefSection] = []
    for raw_section in value:
        if not isinstance(raw_section, dict):
            continue
        sections.append(
            DailyBriefSection(
                kind=DailyBriefSectionKind(str(raw_section["kind"])),
                title=str(raw_section.get("title") or raw_section["kind"]),
                coverage=SourceCoverage(str(raw_section["coverage"])),
                freshness=FreshnessStatus(str(raw_section["freshness"])),
                items=tuple(_items_from_arguments(raw_section.get("items"))),
                warnings=tuple(_strings_from_arguments(raw_section.get("warnings"))),
                evidence_refs=tuple(_strings_from_arguments(raw_section.get("evidence_refs"))),
            )
        )
    return sections


def _unavailable_sections_from_arguments(value: object) -> list[UnavailableBriefSection]:
    if not isinstance(value, list):
        return []
    sections: list[UnavailableBriefSection] = []
    for raw_section in value:
        if not isinstance(raw_section, dict):
            continue
        sections.append(
            UnavailableBriefSection(
                kind=DailyBriefSectionKind(str(raw_section["kind"])),
                reason=str(raw_section["reason"]),
                evidence_refs=tuple(_strings_from_arguments(raw_section.get("evidence_refs"))),
            )
        )
    return sections


def _items_from_arguments(value: object) -> list[DailyBriefItem]:
    if not isinstance(value, list):
        return []
    items: list[DailyBriefItem] = []
    for raw_item in value:
        if not isinstance(raw_item, dict):
            continue
        items.append(
            DailyBriefItem(
                label=str(raw_item.get("label", "")),
                value=str(raw_item.get("value", "")),
                detail=str(raw_item.get("detail", "")),
                evidence_refs=tuple(_strings_from_arguments(raw_item.get("evidence_refs"))),
            )
        )
    return items


def _strings_from_arguments(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _dict_from_arguments(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return dict(value)


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
