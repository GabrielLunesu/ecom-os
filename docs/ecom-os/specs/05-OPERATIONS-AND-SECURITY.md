# 05 — Operations and Security

> **Status:** normative production operations baseline  
> **Last reviewed:** 2026-06-18  
> **Applies to:** one self-hosted Ecom-OS instance and its dedicated Hermes profile

## 1. Operating model

Ecom-OS is owner-operated software. The instance owner controls the VPS, source,
configuration, Hermes profile, connected accounts, autonomy settings, extensions, and
retention policy. The supported product must make risky choices explicit and traceable;
it must not claim to make an owner unable to change their own system.

The security goal is therefore:

> Protect the operator's intended identity, scope, data, and action semantics from
> accidental or unauthorized change while preserving an explicit owner escape hatch.

This document separates two kinds of control:

- **Business-risk controls** — approval requirements, spend/refund/discount caps,
  allowed action classes, schedules, and escalation policies. The owner may relax or
  disable these, including selecting `unrestricted` for a granted tool.
- **Technical-integrity controls** — authentication, exact store/account binding,
  schema validation, idempotency, action recording, redaction, and outcome
  reconciliation. These remain active in every supported autonomy mode because they
  preserve what the operator meant to do.

Unrestricted autonomy is not a hidden “safe mode.” It can lose money, damage customer
relationships, alter products, or create legal exposure. Ecom-OS records the enabling
change, presents the affected tools and scopes, and then respects the owner's choice.

## 2. Production topology

The supported deployment places all internal services on a private network.

```text
Internet
   │
   ▼
reverse proxy / TLS / rate limits
   │
   ├── /              → ecom-web
   ├── /api/*         → ecom-api
   ├── verified webhooks → ecom-api ingress
   └── no public route → Postgres / Hermes service endpoints / worker

private network
   ├── ecom-api
   ├── ecom-worker
   ├── Postgres
   ├── Hermes gateway/API/TUI bridge
   └── optional connector services
```

Requirements:

- TLS terminates at a maintained reverse proxy or trusted platform load balancer.
- Postgres is never publicly routable.
- Hermes programmatic endpoints bind to loopback or the private service network and
  require their supported authentication mechanism.
- The browser communicates with Ecom-OS, not directly with Hermes using a service key.
- Webhook routes are separated from authenticated browser routes and verify provider
  signatures before accepting an event.
- Workers have no public listener unless a specific signed callback requires one.
- Development convenience ports are not exposed in production Compose profiles.

A single-host deployment is supported. Process separation still matters: a compromise of
`ecom-web` should not automatically provide the Postgres superuser password, Hermes
profile secrets, or every connector credential.

## 3. Identity and authorization

### 3.1 Human identities

Production access requires an authenticated Ecom-OS user. Password authentication, OIDC,
or another supported identity provider may be used, but the selected method must provide:

- unique stable user IDs;
- secure session expiry and revocation;
- multi-factor authentication for owner/admin roles where the provider supports it;
- auditable login, logout, recovery, and role changes;
- protection against session fixation and CSRF;
- rate limiting and lockout or upstream abuse protection.

The first user becomes `owner` through an explicit bootstrap flow. Bootstrap closes after
ownership is established and can only be re-opened from the host with a recovery command.

### 3.2 Roles and scopes

Roles grant Ecom-OS page, data, configuration, approval, and tool scopes. They do not
implicitly grant Hermes gateway access, and Hermes gateway access does not implicitly
create an Ecom-OS identity.

Sensitive operations require recent authentication and the appropriate role:

- ownership transfer;
- changing unrestricted autonomy;
- installing trusted native code;
- revealing or rotating service credentials;
- deleting traces or shortening retention;
- disconnecting a store;
- restoring a backup;
- changing channel identity mappings;
- approving actions above configured thresholds.

### 3.3 Channel identities

Messages arriving through Hermes native channels are mapped to Ecom-OS users by a
`channel_identity` record. The mapping includes platform, platform account/bot, chat or
channel, platform user, Ecom-OS user, role snapshot, status, and verification time.

Rules:

- An unmapped sender receives no privileged Ecom-OS identity by inference.
- A group/channel mapping does not automatically authorize every member; authorization
  may be per sender or restricted to read-only group commands.
- The effective Ecom-OS role is re-resolved at tool invocation time, not cached forever
  in a chat transcript.
- Removing a mapping revokes future Ecom-OS tool access without deleting Hermes history.
- Native Hermes allowlists, pairing, and channel permissions remain an additional outer
  layer and should be enabled.

### 3.4 Service identities

The Hermes adapter, MCP client, workers, update controller, and connector callbacks use
separate service identities. Each identity has:

- a unique ID and credential;
- an explicit audience;
- narrow scopes;
- creation, last-used, rotation, and revocation timestamps;
- no ability to impersonate arbitrary humans unless the contract explicitly requires and
  records an acting user.

Shared all-powerful machine tokens are prohibited in the supported deployment.

## 4. Secret and credential model

The statement “Ecom-OS stores connection references, not merchant OAuth tokens” applies
when a managed connector provider such as Composio owns the OAuth lifecycle. It does not
mean the deployment contains no secrets. The system necessarily has service keys, model
provider credentials, cookie/session secrets, database passwords, and possibly direct
connector credentials.

### 4.1 Secret classes

| Secret class | Canonical location | May be stored in Ecom-OS Postgres? |
|---|---|---:|
| Merchant OAuth via managed connector | connector provider | reference only |
| Direct connector token | encrypted secret store / mounted secret | ciphertext/reference only |
| Hermes model/provider keys | Hermes profile secret mechanism | no plaintext copy |
| Hermes API/service key | runtime secret store | hash/reference only where possible |
| Ecom-OS session/signing keys | runtime secret store | no |
| Postgres credentials | runtime secret store | no |
| Adapter/MCP machine credential | runtime secret store; hashed verifier in Ecom-OS | verifier only |
| OAuth client secret owned by instance | runtime secret store | no plaintext |

A local `.env` file is acceptable for a small self-hosted deployment only when it is:

- outside version control;
- permissioned to the service account;
- excluded from backups that leave the operator's trust boundary unless encrypted;
- never mounted into services that do not need the values;
- replaceable by Docker/Kubernetes/system secret mechanisms.

Do not pass the Composio key, Hermes key, or direct connector credentials into the
frontend, Ecom-OS plugins, or unrelated Hermes tools.

### 4.2 Logging and output rules

- Secret fields are redacted at structured-logging boundaries, not by ad hoc string
  replacement after serialization.
- Authorization headers, cookies, tokens, private keys, webhook signatures, and complete
  connection payloads are never logged.
- Tool results return connection IDs and provider operation IDs, never bearer tokens.
- Exception reporters receive scrubbed metadata.
- Trace raw payload retention requires field-level classification and restricted access.
- A secret-detection test corpus runs against logs and exported traces in CI.

### 4.3 Rotation and revocation

Every production runbook defines how to rotate:

- Ecom-OS signing/session keys;
- Hermes service credentials;
- adapter and MCP credentials;
- database credentials;
- connector provider keys;
- direct connector tokens;
- webhook secrets.

Rotation must support overlapping validity where necessary so a live instance can change
keys without dropping durable work. Revocation is audited and invalidates cached sessions
or service credentials as soon as practical.

## 5. Hermes integration hardening

Hermes is a trusted peer, not a sandbox supplied by Ecom-OS. A dedicated profile reduces
accidental cross-brand state sharing but is not an operating-system security boundary.

Production requirements:

- Pin Hermes to a tested compatibility range and record the exact version at runtime.
- Pin the Ecom-OS Hermes adapter version and schema hash.
- Run the startup capability probe before enabling dependent features.
- Keep Hermes programmatic endpoints private and authenticated.
- Give the adapter an instance/profile-scoped Ecom-OS service identity.
- Use explicit MCP tool includes; do not expose every discoverable tool by default.
- Keep model keys and channel tokens in the Hermes profile's supported secret mechanism.
- Back up the complete active profile, including `state.db`, memory, skills, cron, and
  gateway configuration.
- Never write to Hermes `state.db` from Ecom-OS. Use supported protocols for history and
  session operations.
- Surface whether a trace came through the adapter, MCP, native Hermes tooling, or an
  unknown path.

Hermes terminal, browser, code execution, arbitrary third-party MCP, and owner-installed
plugins may create side effects outside the Ecom-OS action executor. Ecom-OS may observe
such activity through supported hooks, but it must not label that coverage `verified`
unless it can independently establish the operation and outcome.

## 6. Connector security

### 6.1 Exact binding

Every Ecom-OS connector operation carries:

- `brand_id`;
- `store_id`;
- `connection_id`;
- connector type and adapter version;
- credential reference;
- actor/service identity;
- action or synchronization trace ID.

“Default account,” “latest connected account,” and other implicit selection are not valid
for an Ecom-OS write. The executor rejects missing or ambiguous binding even in
`unrestricted` mode.

### 6.2 Managed connector providers

When Composio or another provider is used:

- store only the provider connection reference and non-secret metadata;
- create sessions with the exact entity/user and connected account;
- provide an explicit tool allowlist for agent-facing sessions;
- avoid connection-management, discovery, shell/workbench, or arbitrary proxy tools in
  operational agent grants unless the owner knowingly installs them outside Ecom-OS;
- record provider request/operation identifiers in action attempts;
- health-check the exact account, not merely the provider API.

### 6.3 Direct connectors

A direct connector adapter must declare:

- authentication method;
- required scopes;
- signature verification rules;
- provider idempotency support;
- rate-limit behavior;
- retry classification;
- reconciliation strategy;
- data retention and deletion behavior;
- sandbox/test support.

Direct adapters run through the same action and trace contracts as managed-provider
adapters.

## 7. Webhook and inbound-event security

An inbound event is not accepted merely because it is valid JSON.

Ingress performs, in order:

1. request-size and content-type checks;
2. provider/source route resolution;
3. signature or HMAC verification against the raw body;
4. timestamp/replay-window validation where supported;
5. source/account binding;
6. durable insertion of the raw event envelope and unique provider event key;
7. a fast success or retryable response according to provider semantics;
8. asynchronous normalization and processing.

Additional rules:

- Preserve the raw body or a cryptographic hash according to retention policy.
- Never let ticket text, email HTML, order notes, or webhook fields select credentials,
  grants, prompts, skills, or policies.
- Sanitize active HTML before rendering.
- Fetch external URLs only through an allowlisted and instrumented service.
- Attach provenance and trust labels to extracted facts.
- Duplicate delivery is normal and must resolve to the same accepted event.
- Invalid signatures never enter the operational event stream.

Hermes webhooks may trigger agent work, but business webhooks should first enter the
Ecom-OS durable inbox so replay and state transitions remain deterministic.

## 8. Autonomy operations

### 8.1 Effective autonomy

The effective decision for a tool invocation is computed from:

- authenticated actor and channel identity;
- Hermes profile and agent/run identity;
- tool and schema version;
- brand/store/connection/entity scope;
- active grant;
- selected mode: `disabled`, `observe`, `approve`, `policy`, or `unrestricted`;
- optional policy result;
- technical-integrity validation.

A mode change is a privileged administrative event containing old/new value, scope,
actor, reason, timestamp, and affected tool inventory.

### 8.2 Enabling unrestricted mode

The supported UI requires the owner to:

- select the exact tool or tool group and store scope;
- review concrete side effects the capability permits;
- acknowledge that business caps and Ecom-OS approval are bypassed;
- choose whether the grant expires;
- enter a reason;
- re-authenticate for high-risk classes;
- confirm the final effective-grant summary.

There is no secret platform maximum presented as “unrestricted.” Provider and legal
limits still exist, and malformed or technically unsafe requests still fail.

### 8.3 Emergency controls

The owner can perform the following independently:

- pause new Ecom-OS external writes;
- pause a tool, store, connector, ticket queue, or all automation;
- revoke a Hermes adapter/MCP credential;
- disable background run creation while leaving chat available;
- stop workers after current leases expire;
- quarantine a connection;
- require approval for all writes;
- rotate credentials;
- mark an action or incident for reconciliation.

Emergency pause does not delete queued work. Resuming displays the backlog and allows the
owner to cancel, simulate, or execute eligible actions.

## 9. Backup architecture

A valid Ecom-OS backup is a **full-instance recovery set**, not only a Postgres dump.

### 9.1 Required backup components

1. Ecom-OS Postgres, including event inbox/outbox, jobs, actions, traces, configuration,
   users, and business data.
2. The active Hermes profile, including `state.db` plus WAL/SHM as appropriate, memory,
   user profile, skills, SOUL/config, cron jobs, gateway config, and profile-local files.
3. The document vault and uploaded artifact store.
4. Ecom-OS extension code/configuration and extension lock/manifest files.
5. Deployment configuration excluding unencrypted secret export where policy forbids it.
6. A backup manifest containing software versions, schema versions, checksums, timestamps,
   instance/brand ID, and encrypted-secret restoration instructions.

Connector-provider OAuth tokens generally remain with the provider. The recovery set must
include connection references and a post-restore verification step; it must never assume
those external connections are still valid.

### 9.2 Consistency procedure

For a planned snapshot:

1. enter maintenance mode;
2. stop leasing new jobs and wait for bounded in-flight work;
3. keep verified ingress buffered or return provider-safe retry responses;
4. record a consistency marker in Postgres;
5. create a transactionally consistent Postgres backup;
6. checkpoint or cleanly stop the Hermes process before copying its SQLite/profile state,
   or use the current supported Hermes backup command;
7. snapshot files and extensions;
8. write and sign/hash the manifest;
9. restart services and drain buffered events;
10. verify a sample restore asynchronously on a separate host according to policy.

Crash-consistent infrastructure snapshots may supplement this process, but the recovery
runbook must describe SQLite WAL and Postgres consistency explicitly.

### 9.3 Backup schedule and targets

Default small-instance profile:

- nightly full logical backup;
- encrypted off-host retention;
- optional continuous Postgres WAL/archive or more frequent snapshots for a lower RPO;
- backup before every supported update and destructive administrative operation;
- monthly restore drill;
- quarterly full disaster-recovery exercise including Hermes and connectors.

Recommended initial targets:

- **RPO:** 24 hours with nightly backup; 15 minutes when continuous database protection
  is enabled. External actions since the backup are re-imported/reconciled where upstream
  APIs permit.
- **RTO:** four hours for the supported single-host profile after infrastructure exists.

These are product targets, not guarantees. The System page must show the active backup
profile, last successful backup, last verified restore, and unmet target.

### 9.4 Restore procedure

A restore is performed into an isolated environment first when possible:

1. verify manifest and checksums;
2. install exact compatible Ecom-OS, Hermes, adapter, and extension versions;
3. restore Postgres and run only the documented compatible migration path;
4. restore the Hermes profile without directly rewriting its schema;
5. restore vault/artifacts/extensions;
6. inject or rotate runtime secrets;
7. run structural health and conformance checks;
8. keep all external writes paused;
9. reconcile connections, pending actions, webhooks, and upstream state;
10. explicitly enable traffic and automation.

Never replay an action solely because its pre-backup local state says `executing` or
`failed`. Reconcile it first.

## 10. Updates and releases

Ecom-OS and Hermes have independent release lifecycles.

### 10.1 Release identity

A supported Ecom-OS release has:

- semantic/product version;
- immutable source commit and, when published, container image digest;
- dependency lockfiles;
- database migration range;
- minimum/maximum tested Hermes range;
- adapter/MCP schema version;
- extension API version;
- signed or checksummed release manifest;
- release notes with known operational risks.

The supported updater deploys an exact release. `git pull` of a moving branch is a source
workflow, not a reproducible production update.

### 10.2 Update sequence

1. preflight disk, backup, extension compatibility, DB version, and Hermes capability;
2. enter maintenance mode and stop new job leases;
3. preserve verified inbound events through buffering or retry behavior;
4. produce and verify the full-instance backup;
5. fetch and verify the exact Ecom-OS release;
6. run expand-compatible migrations;
7. start the candidate API/worker version with external writes paused;
8. run schema, health, Hermes conformance, connector-read, and action-simulation checks;
9. resume jobs and writes in stages;
10. monitor error, queue, action, and trace-gap rates;
11. record the completed update as an audit event.

Destructive contract migrations are separated into later releases after all supported
code versions no longer depend on old fields.

### 10.3 Rollback

Application rollback is allowed only when the database and extension versions remain
backward compatible. Otherwise the recovery action is restore or a forward fix. The
updater must not promise a one-click rollback after an irreversible migration.

Hermes upgrades follow Hermes's supported mechanism and are followed by the Ecom-OS
capability probe and conformance suite before automation resumes.

## 11. Health and degraded modes

### 11.1 Health dimensions

The System page and `/health` APIs distinguish:

- process liveness;
- readiness to serve authenticated reads;
- readiness to start Hermes runs;
- readiness to execute external writes;
- connector health by exact connection;
- queue and lease health;
- action reconciliation backlog;
- trace ingest lag/gaps;
- backup freshness;
- Hermes/adapter compatibility;
- extension compatibility.

A single green/red light is insufficient.

### 11.2 Degradation matrix

| Failure | Reads | Chat | New agent jobs | External writes | Required operator signal |
|---|---|---|---|---|---|
| Hermes unavailable | last-good/current Ecom data | unavailable/degraded | pause | deterministic writes may remain if human-authorized | prominent banner + alert |
| Postgres unavailable | unavailable/limited cache | Hermes non-Ecom chat may continue | stop | stop | critical alert |
| One connector down | last-good with freshness | available | jobs may continue without that dependency | queue/fail per action | connection-level banner |
| Adapter telemetry down | available | available | available | Ecom tools remain verified | trace coverage warning |
| Ecom API down | unavailable | native Hermes may remain | stop Ecom-triggered | stop Ecom actions | service alert |
| Model/provider down | available | degraded | retry/escalate | no new agent-proposed writes | provider alert |
| Reconciliation unhealthy | available | available | available | high-risk ambiguous retries pause | critical action warning |

No connector outage may silently present stale data as current.

## 12. Monitoring and alerting

Minimum operational metrics:

- request/error/latency by route;
- database connections, locks, replication/backup status;
- event inbox lag and duplicate rate;
- runnable/leased/expired/dead jobs;
- outbox lag;
- Hermes health, version, run starts/completions/failures;
- adapter telemetry acceptance and reconciliation gaps;
- tool calls by status and coverage;
- actions by state, especially `outcome_unknown`;
- connector rate-limit and authentication failures;
- ticket backlog, autonomous resolution, reopen, and escalation rates;
- daily brief generation/delivery status;
- last successful backup and restore test;
- unrestricted-grant count and recent changes.

Alerts are actionable and linked to the relevant System page, trace, connection, or
incident. Repeated transient failures should aggregate rather than flood channels.

## 13. Incident response

### 13.1 Incident classes

- duplicate or incorrect external action;
- unexpected financial loss or discount/refund pattern;
- wrong-store or wrong-customer action;
- prompt-injection-influenced behavior;
- credential exposure or unauthorized access;
- missing/partial trace coverage;
- connector outcome ambiguity;
- data corruption or migration failure;
- missed ticket/message or daily brief;
- performance/availability degradation.

### 13.2 Response flow

1. **Detect and open:** create an incident linked to alerts, traces, actions, tickets,
   users, connections, and software versions.
2. **Contain:** pause the smallest affected scope; revoke credentials or grants when
   required.
3. **Preserve:** retain relevant traces, payload hashes, configuration versions, and
   provider evidence. Do not “clean up” before capture.
4. **Reconcile:** determine the actual external state using provider APIs and customer
   records.
5. **Explain:** identify whether the primary cause was agent judgment, prompt/skill,
   owner grant/policy, stale/incorrect data, connector behavior, software defect, human
   action, or unknown.
6. **Repair:** compensate or correct where permitted, then replay deterministic work.
7. **Learn:** add a test, monitor, policy/template improvement, or documentation change.
8. **Close:** record impact, timeline, root cause confidence, and follow-up owners.

Hermes receives read-only trace/incident tools so the owner can ask the agent to inspect a
problem. The agent's diagnosis is recorded as analysis, not silently promoted to root
cause without supporting evidence.

## 14. Privacy, retention, and deletion

The operator is responsible for applicable privacy and data-retention obligations.
Ecom-OS provides controls to support that responsibility:

- data classification and access labels;
- configurable retention classes;
- redaction of secrets and unnecessary PII;
- restricted raw payload access;
- export and deletion workflows;
- legal-hold/incident hold where configured;
- audit of deletion and retention changes;
- separation of customer-facing data from founder-private material.

Deleting Ecom-OS trace content does not automatically delete the corresponding Hermes
session, channel history, upstream ticket, or connector-provider record. The deletion UI
must show each system and perform supported deletions separately.

Trace retention defaults should preserve operational usefulness without retaining every
raw payload forever. Summaries, hashes, entity references, and action outcomes may outlive
redacted raw content according to policy.

## 15. Trusted extensions and host access

A trusted native Ecom-OS extension or arbitrary Hermes plugin is software installed by the
owner. It may be able to read files, environment variables, network services, or databases
beyond its declared manifest depending on process isolation.

Supported behavior:

- installation requires owner authorization;
- source, version, checksum/signature where available, requested capabilities, and trust
  class are shown;
- enabled/disabled/version changes are audited;
- extensions use separate processes and narrow credentials where practical;
- extension health and compatibility are visible;
- Ecom-OS does not claim complete traceability for operations that bypass its contracts.

A manifest is metadata, not proof of sandboxing.

## 16. Production-readiness checklist

An instance is production-ready only when all applicable checks pass:

### Identity and network

- [ ] Owner bootstrap is closed.
- [ ] TLS and secure cookies are enabled.
- [ ] Postgres and Hermes service endpoints are private.
- [ ] Owner/admin MFA is enabled where supported.
- [ ] Channel identities and Hermes channel allowlists are reviewed.

### Hermes

- [ ] Exact Hermes and adapter versions are recorded and supported.
- [ ] Capability probe and conformance suite pass.
- [ ] Main chat can create/resume/interrupt a test session.
- [ ] Ecom-OS tools are discoverable with the intended include list.
- [ ] A native channel test message and scheduled delivery succeed.

### Data and connectors

- [ ] Store and inbox webhooks verify signatures.
- [ ] Duplicate event tests pass.
- [ ] Exact account binding is confirmed for every connection.
- [ ] Initial synchronization is complete or freshness gaps are visible.
- [ ] Connector read and write simulations pass.

### Actions and traceability

- [ ] Every supported write creates a trace, action, and attempt.
- [ ] Timeout/`outcome_unknown` reconciliation is tested.
- [ ] Approval digest/expiry tests pass where enabled.
- [ ] Unrestricted-mode enable/disable is audited.
- [ ] Trace search can locate work by ticket, order, customer, action, date, and run.

### Recovery

- [ ] Full-instance backup completes and verifies.
- [ ] Restore drill includes Postgres, Hermes profile, vault, and extensions.
- [ ] Pending actions are reconciled before writes resume after restore.
- [ ] Backup and recovery targets are displayed on the System page.

### Operations

- [ ] Queue, action, connector, Hermes, and backup alerts are routed.
- [ ] Emergency pause is tested.
- [ ] Incident runbook and responsible contacts are configured.
- [ ] Daily brief has a deterministic fallback and delivery trace.

## 17. Known limits

Even a conforming production deployment cannot guarantee:

- that an unrestricted agent will make good business decisions;
- complete observation of arbitrary terminal/browser/third-party tool activity;
- recovery of upstream data a provider no longer exposes;
- automatic rollback of destructive migrations;
- tamper resistance against the VPS owner/root user;
- compliance with every jurisdiction without operator configuration and legal review.

The product promise is narrower and testable: supported Ecom-OS operations are
identity-bound, durable, traceable, idempotent, and recoverable, and uncertainty is shown
rather than hidden.
