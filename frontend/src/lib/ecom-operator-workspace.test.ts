import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/api/mutator", () => ({
  customFetch: vi.fn(),
}));

import { customFetch } from "@/api/mutator";
import {
  buildTodayAttentionInputs,
  createAskHermesIntent,
  createOperatorTask,
  fetchOperatorTasks,
  fetchKnowledgeDocument,
  fetchTodayAttention,
  roleTestKnowledge,
  todayFreshnessLabel,
  todaySourceHref,
  todayTraceHref,
  todayUnavailableDependencies,
  updateOperatorTask,
  upsertKnowledgeDocument,
  type AttentionInput,
  type AttentionItem,
  type Connections,
  type Insight,
  type Metrics,
  type OperatorTask,
} from "./ecom-api";

const customFetchMock = vi.mocked(customFetch);

const fulfilled = <T>(value: T): PromiseFulfilledResult<T> => ({
  status: "fulfilled",
  value,
});

const rejected = (): PromiseRejectedResult => ({
  status: "rejected",
  reason: new Error("unavailable"),
});

const baseMetrics: Metrics = {
  scope: "all",
  days: 1,
  kpis: {
    revenue: 1200,
    orders: 10,
    aov: 120,
    currency: "USD",
    sessions: null,
    conversion: null,
    atc_rate: null,
  },
  per_store: [],
  unavailable: {},
};

const baseConnections: Connections = {
  ready: true,
  providers: [],
};

const baseTask: OperatorTask = {
  id: "task-1",
  brand_id: "brand-1",
  title: "Call supplier",
  description: null,
  status: "todo",
  priority: "urgent",
  due_at: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
  assignee_type: "external",
  assignee_id: null,
  assignee_label: "Sam",
  provenance: "agent",
  created_by_actor_type: "hermes_profile",
  created_by_actor_id: "agent-1",
  source_trace_id: "trace-1",
  source_run_id: "run-1",
  source_evidence_ref: "ticket:1",
  access_label: "operations",
  daily_brief_include: true,
  entity_links: [],
  comments: [],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const toSnapshotItem = (
  input: AttentionInput,
  index: number,
): AttentionItem => ({
  ...input,
  summary: input.summary ?? "",
  severity: input.severity ?? "info",
  source_status: input.source_status ?? "available",
  coverage: input.coverage ?? "unknown",
  trace_id: input.trace_id ?? null,
  source_refs: input.source_refs ?? [],
  freshness_as_of: input.freshness_as_of ?? null,
  primary_action: input.primary_action ?? null,
  reasons: input.reasons ?? [],
  rank: index + 1,
  score: 100 - index,
  unavailable_dependencies:
    input.source_status === "unavailable" ? [input.kind] : [],
});

afterEach(() => {
  customFetchMock.mockReset();
  vi.restoreAllMocks();
});

describe("buildTodayAttentionInputs", () => {
  it("marks failed sources unavailable instead of zero", () => {
    const inputs = buildTodayAttentionInputs({
      tasks: rejected(),
      connections: fulfilled(baseConnections),
      metrics: fulfilled(baseMetrics),
      tickets: rejected(),
      insights: fulfilled<Insight[]>([]),
    });

    expect(inputs).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          kind: "due_tasks",
          source_status: "unavailable",
          title: "Task source unavailable",
        }),
        expect.objectContaining({
          kind: "cs_backlog",
          source_status: "unavailable",
          title: "CS backlog source unavailable",
        }),
      ]),
    );
  });

  it("creates due task and health source refs without computing finance", () => {
    const inputs = buildTodayAttentionInputs({
      tasks: fulfilled([baseTask]),
      connections: fulfilled({
        ready: false,
        providers: [
          { provider: "shopify", connected: false, detail: "token expired" },
        ],
      }),
      metrics: fulfilled(baseMetrics),
      tickets: fulfilled([]),
      insights: fulfilled([]),
    });

    expect(inputs).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          kind: "due_tasks",
          severity: "high",
          trace_id: "trace-1",
          source_refs: [
            expect.objectContaining({ type: "task", id: "task-1" }),
          ],
        }),
        expect.objectContaining({
          kind: "health",
          source_status: "partial",
          source_refs: [
            expect.objectContaining({ type: "connection", id: "shopify" }),
          ],
        }),
        expect.objectContaining({
          kind: "metrics",
          coverage: "imported",
          reasons: expect.arrayContaining([
            "A08 metric snapshot contract pending",
          ]),
        }),
      ]),
    );
  });
});

describe("fetchTodayAttention", () => {
  it("persists normalized inputs through the snapshot endpoint", async () => {
    vi.spyOn(Date, "now").mockReturnValue(
      Date.parse("2026-06-19T12:00:00.000Z"),
    );

    customFetchMock.mockImplementation(async (url, options) => {
      if (url === "/api/v1/ecom/operator-workspace/tasks?role=operator") {
        return {
          data: [
            {
              ...baseTask,
              due_at: "2026-06-19T13:00:00.000Z",
            },
          ],
          status: 200,
        };
      }
      if (url === "/api/v1/ecom/connections") {
        return { data: baseConnections, status: 200 };
      }
      if (url === "/api/v1/ecom/metrics?store=all&days=1") {
        return { data: baseMetrics, status: 200 };
      }
      if (url === "/api/v1/ecom/tickets") {
        return { data: [], status: 200 };
      }
      if (url === "/api/v1/ecom/insights") {
        return { data: [], status: 200 };
      }
      if (url === "/api/v1/ecom/operator-workspace/attention/snapshots") {
        const body = JSON.parse(String(options.body)) as {
          inputs: AttentionInput[];
          window_start: string;
          window_end: string;
        };

        expect(body.window_start).toBe("2026-06-18T12:00:00.000Z");
        expect(body.window_end).toBe("2026-06-19T12:00:00.000Z");
        expect(body.inputs).toEqual(
          expect.arrayContaining([
            expect.objectContaining({
              kind: "due_tasks",
              trace_id: "trace-1",
            }),
            expect.objectContaining({
              kind: "approvals",
              source_status: "unavailable",
            }),
          ]),
        );

        return {
          data: {
            id: "snapshot-1",
            brand_id: "brand-1",
            status: "ready",
            source_status: "partial",
            window_start: body.window_start,
            window_end: body.window_end,
            input_count: body.inputs.length,
            item_count: body.inputs.length,
            inputs: body.inputs,
            items: body.inputs.map(toSnapshotItem),
            created_at: "2026-06-19T12:00:01.000Z",
          },
          status: 201,
        };
      }

      throw new Error(`unexpected URL ${url}`);
    });

    const snapshot = await fetchTodayAttention();

    expect(snapshot.id).toBe("snapshot-1");
    expect(snapshot.items).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ kind: "due_tasks", trace_id: "trace-1" }),
      ]),
    );
    expect(customFetchMock).toHaveBeenCalledWith(
      "/api/v1/ecom/operator-workspace/attention/snapshots",
      expect.objectContaining({
        method: "POST",
        body: expect.any(String),
      }),
    );
  });
});

describe("createAskHermesIntent", () => {
  it("sends only safe entity refs and prompt metadata", async () => {
    customFetchMock.mockResolvedValueOnce({
      data: {
        surface: "tasks",
        entity_refs: [
          {
            entity_type: "task",
            entity_id: "task-1",
            label: "Call supplier",
            trace_id: "00000000-0000-4000-8000-000000000001",
          },
        ],
        trace_id: "00000000-0000-4000-8000-000000000001",
        suggested_prompt: "Inspect task Call supplier",
        access_label: "operations",
        ttl_seconds: 600,
      },
      status: 200,
    });

    const intent = await createAskHermesIntent({
      surface: "tasks",
      entity_refs: [
        {
          entity_type: "task",
          entity_id: "task-1",
          label: "Call supplier",
          trace_id: "00000000-0000-4000-8000-000000000001",
        },
      ],
      trace_id: "00000000-0000-4000-8000-000000000001",
      suggested_prompt: "Inspect task Call supplier",
      access_label: "operations",
    });

    const [, options] = customFetchMock.mock.calls[0];
    const body = JSON.parse(String(options.body)) as Record<string, unknown>;

    expect(customFetchMock).toHaveBeenCalledWith(
      "/api/v1/ecom/operator-workspace/ask-hermes-intents",
      expect.objectContaining({ method: "POST" }),
    );
    expect(body).toMatchObject({
      surface: "tasks",
      suggested_prompt: "Inspect task Call supplier",
      access_label: "operations",
    });
    expect(body).not.toHaveProperty("transcript");
    expect(body).not.toHaveProperty("content");
    expect(body).not.toHaveProperty("body");
    expect(body).not.toHaveProperty("credential");
    expect(intent.ttl_seconds).toBe(600);
    expect(intent.entity_refs).toHaveLength(1);
  });
});

describe("roleTestKnowledge", () => {
  it("uses the role-test endpoint and preserves access-filtered results", async () => {
    customFetchMock.mockResolvedValueOnce({
      data: {
        role: "viewer",
        query: "refund",
        accessible_count: 1,
        results: [
          {
            document_id: "document-public",
            version_id: "version-public",
            title: "Public refund policy",
            logical_path: "policies/refund",
            source: "operator",
            effective_date: "2026-06-19",
            access_label: "public",
            trust_label: "verified",
            supersession_state: "current",
            snippet: "Public refund window",
            evidence_ref: "document_version:version-public",
            ingestion_status: "indexed",
            extraction_status: "indexed",
          },
        ],
      },
      status: 200,
    });

    const response = await roleTestKnowledge("refund", "viewer");
    const [, options] = customFetchMock.mock.calls[0];
    const body = JSON.parse(String(options.body)) as Record<string, unknown>;

    expect(customFetchMock).toHaveBeenCalledWith(
      "/api/v1/ecom/operator-workspace/knowledge/role-test",
      expect.objectContaining({ method: "POST" }),
    );
    expect(body).toEqual({ query: "refund", role: "viewer" });
    expect(response.accessible_count).toBe(response.results.length);
    expect(response.results).toEqual([
      expect.objectContaining({
        access_label: "public",
        snippet: "Public refund window",
      }),
    ]);
    expect(response.results).not.toEqual(
      expect.arrayContaining([
        expect.objectContaining({ access_label: "founder_private" }),
      ]),
    );
  });
});

describe("fetchOperatorTasks", () => {
  it("requests tasks with an explicit access role", async () => {
    customFetchMock.mockResolvedValueOnce({
      data: [{ ...baseTask, access_label: "public" }],
      status: 200,
    });

    const tasks = await fetchOperatorTasks("viewer");

    expect(customFetchMock).toHaveBeenCalledWith(
      "/api/v1/ecom/operator-workspace/tasks?role=viewer",
      { method: "GET" },
    );
    expect(tasks).toEqual([
      expect.objectContaining({
        id: "task-1",
        access_label: "public",
      }),
    ]);
  });
});

describe("createOperatorTask", () => {
  it("sends access label and daily brief inclusion fields", async () => {
    customFetchMock.mockResolvedValueOnce({
      data: {
        ...baseTask,
        access_label: "finance",
        daily_brief_include: false,
      },
      status: 201,
    });

    const task = await createOperatorTask({
      title: "Review payout exception",
      priority: "high",
      access_label: "finance",
      daily_brief_include: false,
      entity_links: [
        {
          entity_type: "order",
          entity_id: "order-1",
          label: "Order 1",
        },
      ],
    });
    const [, options] = customFetchMock.mock.calls[0];
    const body = JSON.parse(String(options.body)) as Record<string, unknown>;

    expect(customFetchMock).toHaveBeenCalledWith(
      "/api/v1/ecom/operator-workspace/tasks",
      expect.objectContaining({ method: "POST" }),
    );
    expect(body).toMatchObject({
      title: "Review payout exception",
      priority: "high",
      access_label: "finance",
      daily_brief_include: false,
    });
    expect(body.entity_links).toEqual([
      expect.objectContaining({
        entity_type: "order",
        entity_id: "order-1",
      }),
    ]);
    expect(task.access_label).toBe("finance");
    expect(task.daily_brief_include).toBe(false);
  });
});

describe("updateOperatorTask", () => {
  it("sends mutable task fields through a role-scoped update", async () => {
    customFetchMock.mockResolvedValueOnce({
      data: {
        ...baseTask,
        priority: "high",
        due_at: "2026-06-20T12:00:00.000Z",
        assignee_type: "external",
        assignee_label: "Support Lead",
        access_label: "cs",
        daily_brief_include: false,
      },
      status: 200,
    });

    const task = await updateOperatorTask(
      "task-1",
      {
        priority: "high",
        due_at: "2026-06-20T12:00:00.000Z",
        assignee_type: "external",
        assignee_label: "Support Lead",
        access_label: "cs",
        daily_brief_include: false,
      },
      "cs_rep",
    );
    const [, options] = customFetchMock.mock.calls[0];
    const body = JSON.parse(String(options.body)) as Record<string, unknown>;

    expect(customFetchMock).toHaveBeenCalledWith(
      "/api/v1/ecom/operator-workspace/tasks/task-1?role=cs_rep",
      expect.objectContaining({ method: "PATCH" }),
    );
    expect(body).toMatchObject({
      priority: "high",
      due_at: "2026-06-20T12:00:00.000Z",
      assignee_type: "external",
      assignee_label: "Support Lead",
      access_label: "cs",
      daily_brief_include: false,
    });
    expect(task.priority).toBe("high");
    expect(task.assignee_label).toBe("Support Lead");
    expect(task.access_label).toBe("cs");
    expect(task.daily_brief_include).toBe(false);
  });
});

describe("upsertKnowledgeDocument", () => {
  it("sends document source, type, effective date, and labels", async () => {
    customFetchMock.mockResolvedValueOnce({
      data: {
        document_id: "document-1",
        version_id: "version-1",
        title: "Warehouse cutoff SOP",
        logical_path: "ops/warehouse-cutoff",
        source: "warehouse_upload",
        effective_date: "2026-06-19",
        access_label: "operations",
        trust_label: "verified",
        supersession_state: "current",
        snippet: "Cutoff is 15:00 UTC",
        evidence_ref: "document_version:version-1",
        ingestion_status: "indexed",
        extraction_status: "indexed",
        body: "<p>Cutoff is 15:00 UTC</p>",
        version_number: 1,
        supersedes_version_id: null,
        checksum: "checksum",
        created_at: "2026-06-19T12:00:00.000Z",
      },
      status: 201,
    });

    const document = await upsertKnowledgeDocument({
      logical_path: "ops/warehouse-cutoff",
      title: "Warehouse cutoff SOP",
      body: "<p>Cutoff is 15:00 UTC</p>",
      document_type: "html",
      source: "warehouse_upload",
      effective_date: "2026-06-19",
      access_label: "operations",
      trust_label: "verified",
    });
    const [, options] = customFetchMock.mock.calls[0];
    const body = JSON.parse(String(options.body)) as Record<string, unknown>;

    expect(customFetchMock).toHaveBeenCalledWith(
      "/api/v1/ecom/operator-workspace/knowledge/documents",
      expect.objectContaining({ method: "POST" }),
    );
    expect(body).toMatchObject({
      logical_path: "ops/warehouse-cutoff",
      title: "Warehouse cutoff SOP",
      document_type: "html",
      source: "warehouse_upload",
      effective_date: "2026-06-19",
      access_label: "operations",
      trust_label: "verified",
    });
    expect(document.source).toBe("warehouse_upload");
    expect(document.effective_date).toBe("2026-06-19");
    expect(document.extraction_status).toBe("indexed");
  });
});

describe("fetchKnowledgeDocument", () => {
  it("requests a specific document version with an explicit role", async () => {
    customFetchMock.mockResolvedValueOnce({
      data: {
        document_id: "document-1",
        version_id: "version-1",
        title: "Warehouse cutoff SOP",
        logical_path: "ops/warehouse-cutoff",
        source: "warehouse_upload",
        effective_date: "2026-06-19",
        access_label: "operations",
        trust_label: "verified",
        supersession_state: "current",
        snippet: "Cutoff is 15:00 UTC",
        evidence_ref: "document_version:version-1",
        ingestion_status: "indexed",
        extraction_status: "indexed",
        body: "Cutoff is 15:00 UTC",
        version_number: 2,
        supersedes_version_id: "version-0",
        checksum: "checksum",
        created_at: "2026-06-19T12:00:00.000Z",
      },
      status: 200,
    });

    const document = await fetchKnowledgeDocument(
      "document-1",
      "operator",
      "version-1",
    );

    expect(customFetchMock).toHaveBeenCalledWith(
      "/api/v1/ecom/operator-workspace/knowledge/documents/document-1?role=operator&version_id=version-1",
      { method: "GET" },
    );
    expect(document.body).toBe("Cutoff is 15:00 UTC");
    expect(document.version_number).toBe(2);
    expect(document.supersedes_version_id).toBe("version-0");
  });
});

describe("todaySourceHref", () => {
  it("links known Today source refs and leaves unavailable dependencies plain", () => {
    expect(todaySourceHref({ type: "task", id: "task-1" })).toBe("/tasks");
    expect(todaySourceHref({ type: "ticket", id: "ticket-1" })).toBe("/cs");
    expect(todaySourceHref({ type: "connection", id: "shopify" })).toBe(
      "/settings",
    );
    expect(todaySourceHref({ type: "metric", id: "legacy" })).toBe(
      "/analytics",
    );
    expect(
      todaySourceHref({ type: "dependency", id: "a02" }, "/overview"),
    ).toBe(null);
    expect(todaySourceHref({ type: "custom", id: "source" }, "/fallback")).toBe(
      "/fallback",
    );
  });
});

describe("todayTraceHref", () => {
  it("links trace ids to the local activity surface", () => {
    expect(todayTraceHref("trace 1")).toBe("/activity?trace=trace%201");
    expect(todayTraceHref(null)).toBeNull();
    expect(todayTraceHref(undefined)).toBeNull();
  });
});

describe("today item evidence helpers", () => {
  it("normalizes unavailable dependencies and freshness evidence", () => {
    expect(
      todayUnavailableDependencies({
        unavailable_dependencies: [" approvals ", "", "incidents"],
      }),
    ).toEqual(["approvals", "incidents"]);
    expect(todayFreshnessLabel("not-a-date")).toBe("not-a-date");
    expect(todayFreshnessLabel(null)).toBeNull();
  });
});
