# Interface Registry

Canonical list of accepted cross-agent contracts. Implementation details remain in the
owner's `INTERFACES.md` and generated schemas.

| Interface | Version | Owner | Consumers | Status | Canonical schema/code | Failure semantics |
|---|---:|---|---|---|---|---|
| Trace context envelope | pending | A01/A02 | all | proposed | — | — |
| Durable action port | pending | A02 | A04/A05/A08 | proposed | — | — |
| Connector adapter port | pending | A04 | A02/A05/A08 | proposed | — | — |
| Hermes bridge | pending | A03 | A05/A07/A08 | proposed | — | — |
| UI token/component contract | pending | A06 | all route owners | proposed | — | — |
| Metric snapshot contract | pending | A08 | A03/A07 | proposed | — | — |

Update rows in place. Superseded versions belong in the durable contract/ADR history, not
as an ever-growing table here.
