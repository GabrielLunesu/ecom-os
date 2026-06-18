# `/goal` Prompt Manifest

All counts include the trailing newline and are below the 4,000-character limit. Copy the
full file, not the summary line.

| Agent | Goal file | Characters | Matching handoff |
|---|---|---:|---|
| A00 | `agent-prompts/goals/A00-program-auditor.goal.md` | 1345 | `agent-prompts/handoffs/A00-program-auditor.md` |
| A01 | `agent-prompts/goals/A01-platform-foundation.goal.md` | 1453 | `agent-prompts/handoffs/A01-platform-foundation.md` |
| A02 | `agent-prompts/goals/A02-durable-core.goal.md` | 1346 | `agent-prompts/handoffs/A02-durable-core.md` |
| A03 | `agent-prompts/goals/A03-hermes-integration.goal.md` | 1384 | `agent-prompts/handoffs/A03-hermes-integration.md` |
| A04 | `agent-prompts/goals/A04-commerce-connectors.goal.md` | 1396 | `agent-prompts/handoffs/A04-commerce-connectors.md` |
| A05 | `agent-prompts/goals/A05-customer-service.goal.md` | 1396 | `agent-prompts/handoffs/A05-customer-service.md` |
| A06 | `agent-prompts/goals/A06-design-system.goal.md` | 1397 | `agent-prompts/handoffs/A06-design-system.md` |
| A07 | `agent-prompts/goals/A07-operator-workspace.goal.md` | 1372 | `agent-prompts/handoffs/A07-operator-workspace.md` |
| A08 | `agent-prompts/goals/A08-finance-brief.goal.md` | 1365 | `agent-prompts/handoffs/A08-finance-brief.md` |
| A09 | `agent-prompts/goals/A09-production-integration.goal.md` | 1478 | `agent-prompts/handoffs/A09-production-integration.md` |

## Validation rule

Before launch, run:

```bash
python - <<'PY'
from pathlib import Path
for p in Path("agent-prompts/goals").glob("A*.goal.md"):
    n = len(p.read_text())
    assert n <= 4000, (p, n)
    assert p.read_text().startswith("/goal "), p
    print(p.name, n)
PY
```
