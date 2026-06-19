# A03 — Hermes Native Integration and Main Chat — Current Risks and Edge Cases

Only open risks remain (resolved items deleted per Operating Protocol §4).

| ID | Risk/edge case | Impact | Current mitigation/status | Owner | Status |
|---|---|---|---|---|---|
| A03-R02 | **No pinned Hermes runtime — real conformance BLOCKED.** No endpoint/credentials/install for a real Hermes v0.16.0. | The seven end-to-end acceptance scenarios cannot be truthfully proven here. | `HermesNativeTransport` reports honest blocked health + refuses ops; the conformance gate keeps every Hermes-dependent feature `not_ready` on fixtures (I-19) and exits 2 BLOCKED; never faked. **Needs IR-A03-05.** | A03 (+ human/infra) | open (blocking) |
| A03-R04 | **Live `mcp_server/server.py` still hand-maintains CS tool names.** The canonical catalog + generator exist, but the live CS MCP server (A05-owned tool names) is not yet sourced from the catalog. | Drift risk persists for the CS tool subset until migrated. | A03 provides the generator (`mcp_server/catalog_server.py`) + drift-guard (`tests/test_catalog_manifest_pinned.py`) for the canonical catalog; live migration needs A05 to register CS tool defs. | A03 + A05 | open |
| A03-R09 | **Repo-wide `black --check` fails on pre-existing non-A03 files.** Baseline files (`agent_runtime/{wismo,flow,in_app}.py`, `models/insight.py`, …) are not black-clean. | `make backend-format-check` is red repo-wide, independent of A03. | A03 files are black/isort clean; non-A03 files untouched (ownership). Flagged to A09 as a baseline condition. | A09 | open (not A03) |

Delete resolved rows after the durable behavior/test/documentation is in place. This is not
an incident history.
