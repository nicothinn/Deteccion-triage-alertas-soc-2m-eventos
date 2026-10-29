---
license: apache-2.0
task_categories:
  - text-classification
  - graph-ml
language:
  - en
tags:
  - cybersecurity
  - intrusion-detection
  - provenance-graphs
  - MITRE-ATT&CK
  - SOAR
  - security-operations
  - IDS
  - network-security
  - threat-detection
  - labeled-dataset
  - lead-rules
pretty_name: WitFoo Precinct6 Cybersecurity Dataset
size_categories:
  - 1M<n<10M
dataset_info:
  - config_name: signals
    splits:
      - name: train
        num_examples: 2011674
  - config_name: incident_signals
    splits:
      - name: train
        num_examples: 238511
configs:
  - config_name: signals
    data_files:
      - split: train
        path: signals/signals.parquet
  - config_name: incident_signals
    data_files:
      - split: train
        path: signals/incident_signals.parquet
  - config_name: graph_nodes
    data_files:
      - split: train
        path: graph/nodes.parquet
  - config_name: graph_edges
    data_files:
      - split: train
        path: graph/edges-*.parquet
  - config_name: attack_reports
    data_files:
      - split: train
        path: graph/attack_reports.parquet
---

# WitFoo Precinct6 Cybersecurity Dataset

**Version 2.1.0** (built 2026-09-22). Regenerated to address feedback from the University of Canterbury
PIDS evaluation: attacks and normal traffic now share a timeline, usernames are wired into the provenance graph,
mis-parsed timestamps are repaired, and every number in this card is generated from the uploaded data.

## Overview

A large-scale, labeled cybersecurity dataset derived from production Security Operations Center (SOC) data
processed by [WitFoo Precinct](https://www.witfoo.com/) version 6.x. It contains **2,011,674 sanitized
security events** captured live from 4 organizations (2024-07-26 11:10:23 UTC to
2024-08-01 06:00:03 UTC), **51,371 incident provenance graphs** with their
238,511 embedded triggering signals, per-incident GraphML files, natural-language attack reports,
and a merged provenance graph (47,585 nodes, 1,740,438 edges).

**Available in two sizes** (same incidents, same methodology, same sanitization registry):
- [`witfoo/precinct6-cybersecurity`](https://huggingface.co/datasets/witfoo/precinct6-cybersecurity) — 2,011,674 live signals, incidents in context (this dataset)
- [`witfoo/precinct6-cybersecurity-100m`](https://huggingface.co/datasets/witfoo/precinct6-cybersecurity-100m) — the full live capture

**Generate your own:** WitFoo Precinct 6.x customers can create datasets from their own data with the
open-source pipeline [`witfoo/dataset-from-precinct6`](https://github.com/witfoo/dataset-from-precinct6).

This dataset supports research in:
- **Provenance graph-based intrusion detection** (KnowHow, NodLink, and similar systems)
- **AI-driven cyber defense simulation** (CybORG and MARL-based defense policy training)
- **Security alert classification** (malicious vs. suspicious vs. benign event labeling)
- **Attack lifecycle analysis** using MITRE ATT&CK framework mappings
- **Detection rule evaluation** using WitFoo's 261 lead detection rules

## What changed in v2

| Issue in v1 | v2 |
|---|---|
| Benign traffic and labeled attacks never overlapped in time (benign from 26 July 2024, incident leads ending 18 July 2024) | `signals` is the live capture labeled **in place**: 7,728 live rows are leads of 1584 incidents observed during the capture, surrounded by their ordinary traffic. Historical incident leads moved to a separate `incident_signals` table with an `origin` column so the two timelines cannot be confused. |
| Usernames existed on signals but credential nodes only inside incident objects | `692,375` **user → host** edges (`USER_ACTION`) join `CREDENTIAL` nodes to the hosts they act on; incident `cred` nodes and live `username` fields share the same `USER-NNNN` tokens. |
| Handful of negative timestamps (Precinct date-parse failures) | Every lead timestamp is validated; 861 were repaired (invalid values from the artifact timeuuid / `rt=` field / incident time; year-rollover errors shifted back by whole years), with the source recorded in `timestamp_source`. No timestamp in either table is outside 2000–2030. |
| README counts drifted from the uploaded files | This card is rendered from the build's `metadata.json`; `signals/metadata.json` and `graph/metadata.json` are uploaded alongside. |
| Incident nodes were keyed by Precinct uuids, disconnected from the live graph | Incident host/credential nodes use the same node ids as live signals (sanitized IP / `user:USER-NNNN`), so incident subgraphs overlay the live graph. |
| Aho-Corasick sweep occasionally corrupted uuids (`id_raw`) inside incidents | Record identifiers are protected from the sweep; leads can be joined to live rows on `artifact_id`. |

### How this subset was drawn

This is the companion **small** dataset. It is a deterministic subset of the full live capture
([`witfoo/precinct6-cybersecurity-100m`](https://huggingface.co/datasets/witfoo/precinct6-cybersecurity-100m)) built for *incidents in context*:

1. every live row that is an incident lead (`malicious`) — 7,728 rows;
2. every live row of the same organization within **±5 minutes** of an in-window incident lead
   (the ordinary traffic around each incident, on the same hosts and network) — 1,606,249 rows;
3. a uniform random fill across the whole capture window (fill probability 0.00371,
   seed 42) — 397,697 rows.

`graph/incidents.jsonl`, `graph/incidents_graphml/` and `graph/attack_reports.jsonl` are identical to the full
dataset. The `signals` table is subsampled, and the merged graph (`graph/nodes.jsonl`, `graph/edges*.jsonl*`,
`graph/graph.graphml`) is rebuilt from the subsampled rows plus all incidents, so its live-derived nodes, edges
and `first_seen` / `last_seen` / `signal_count` attributes describe the subset (counts in `graph/metadata.json`).
Selection parameters are in `build/subset_stats.json`.

## Versions

This is **v2.1.0**. It corrects v2.0.0, which stays available at the `v2.0.0` tag:

| Changed since v2.0.0 | |
|---|---|
| Duplicate incidents | Precinct sometimes raised one incident several times over the same triggering signals. One is kept per set — the one Precinct worked on: an analyst decision first, then the most analysis cycles and the highest suspicion — and the others' ids are listed in `duplicate_incident_ids` (9,204 collapsed). |
| `Disrupted` | `disposition_category` is `automated`: Precinct's engine sets it, and no analyst action is recorded on these incidents. |
| Year-rollover timestamps | Late-December events that Precinct dated a year late are shifted back (835 lead rows, `timestamp_source = lead.observed_at.year_repaired`); `incidents.jsonl` keeps the originals in `_*_raw` fields. |
| Organization tokens | An incident `org` field holding the organization's display name carries the organization's own token, as `_org_id` does. |
| `suspicious` rows | Carry the MITRE techniques of their matched rules' set roles. |

Tokens are shared with v2.0.0 (this build reused its PII registry), apart from the incident `org` fields above
and fewer than 200 values, mostly email addresses, whose registry entries were re-created and renumbered.

```python
from datasets import load_dataset

signals = load_dataset("witfoo/precinct6-cybersecurity", "signals", split="train")                          # v2.1.0
signals_v2_0 = load_dataset("witfoo/precinct6-cybersecurity", "signals", split="train", revision="v2.0.0")  # previous release
```

The 2026-05 release (v1) is not kept for download. Re-verifying it against the v2 tooling showed that
some values had escaped sanitization — device and account names survived inside JSON-escaped Windows
event text and in `stream_name` — so it was withdrawn rather than preserved at a tag. Its tokens are not
comparable with v2: each used its own registry, so `HOST-0042` there is a different machine from
`HOST-0042` here.

## Quick Start

```python
from datasets import load_dataset

REPO = "witfoo/precinct6-cybersecurity"

# Live capture, labeled in place (benign / suspicious / malicious share hosts and hours)
signals = load_dataset(REPO, "signals", split="train")

# In-window attacks with their surrounding traffic: filter on the incident ids
attacks = signals.filter(lambda x: x["label_binary"] == "malicious")

# Historical incident leads (2022–2024) — a separate timeline, same columns
incident_signals = load_dataset(REPO, "incident_signals", split="train")

# Provenance graph: hosts + credentials, host->host event edges, user->host edges, incident links
nodes = load_dataset(REPO, "graph_nodes", split="train")
edges = load_dataset(REPO, "graph_edges", split="train")

# Deterministic attack reports (one per incident)
reports = load_dataset(REPO, "attack_reports", split="train")

# Full incident graphs (nested dicts keyed by uuid; not a typed config)
import pandas as pd
incidents = pd.read_json("hf://datasets/" + REPO + "/graph/incidents.jsonl", lines=True)
```

Join an incident lead to its live row: `incident_signals.artifact_id == signals.artifact_id`
(both are the Precinct artifact timeuuid). Rows of `signals` that are leads carry the incident ids in
`incident_ids`.

## Temporal coverage

**`signals` (live capture, `origin = live`)** — 2,011,674 rows, 2024-07-26 11:10:23 UTC → 2024-08-01 06:00:03 UTC

| Label | Rows | Share | Earliest | Latest |
|---|---|---|---|---|
| `benign` | 1,897,153 | 94.31% | 2024-07-26 11:10:23 UTC | 2024-08-01 06:00:03 UTC |
| `suspicious` | 106,793 | 5.31% | 2024-07-26 11:10:48 UTC | 2024-08-01 02:56:24 UTC |
| `malicious` | 7,728 | 0.38% | 2024-07-26 11:15:48 UTC | 2024-07-30 04:56:35 UTC |

**`incident_signals` (embedded incident leads, `origin = incident_lead`)** — 238,511 rows, 2022-05-30 14:43:45 UTC → 2024-07-28 16:39:47 UTC

| Label | Rows | Share | Earliest | Latest |
|---|---|---|---|---|
| `benign` | 0 | 0.00% | - | - |
| `suspicious` | 0 | 0.00% | - | - |
| `malicious` | 238,511 | 100.00% | 2022-05-30 14:43:45 UTC | 2024-07-28 16:39:47 UTC |

The live capture is the complete artifact retention window of the archived Precinct cluster. Coverage is not
uniform across organizations or days: check the per-organization table below, the per-label time ranges in
`signals/metadata.json`, and the per-organization hourly histogram in `build/label_stats.json` before
assuming a continuous capture.

### Organizations

| Organization | Live rows | Malicious (in place) | Suspicious |
|---|---|---|---|
| `ORG-0004` | 995,985 | 4,176 | 15,115 |
| `ORG-0005` | 576,817 | 3,536 | 91,555 |
| `ORG-0003` | 433,904 | 16 | 113 |
| `ORG-0001` | 4,968 | 0 | 10 |

### Incidents in context

1584 incidents have at least one triggering signal that was found among the live rows; those
7,728 lead artifacts are labeled `malicious` **in place** in `signals` (they are not duplicated
in `incident_signals`). Leads of 49,797 incidents were not found among the live rows (their
incidents pre-date the capture, or the live artifact was not retained) and live in `incident_signals`.

| Incident | Leads matched to live rows |
|---|---|
| `acee85e0-4b4e-11ef-a07e-73bb772fb986` | 501 |
| `04bdda80-4b51-11ef-98d0-55d447741aef` | 445 |
| `ac8def50-4b4e-11ef-a07e-73bb772fb986` | 120 |
| `f4e66920-4df2-11ef-ab9d-d9f9158e7fcb` | 100 |
| `d5e53480-4df1-11ef-b093-ed1dc3d0dbe9` | 100 |
| `d4b9faf0-4df1-11ef-8cc7-db879965e06f` | 100 |
| `d6d64b40-4df1-11ef-9932-fd48ea8ae2b1` | 100 |
| `f1cc09c0-4df2-11ef-9b95-c93931f0c6f5` | 100 |
| `05d71510-4df6-11ef-9440-1101dfaeda6b` | 100 |
| `d3f17ad0-4df1-11ef-9f66-fbdc83d0625f` | 100 |
| `03884310-4df6-11ef-9f66-fbdc83d0625f` | 100 |
| `fec67ca0-4df2-11ef-8cc7-db879965e06f` | 100 |
| `d7813140-4df1-11ef-b093-ed1dc3d0dbe9` | 100 |
| `68809c00-4df5-11ef-8cc7-db879965e06f` | 100 |
| `fdc90270-4df5-11ef-9b95-c93931f0c6f5` | 100 |
| ... | ... |

## Label distribution

Across both tables (2,250,185 rows):

| Label | Rows | Share |
|---|---|---|
| `benign` | 1,897,153 | 84.31% |
| `suspicious` | 106,793 | 4.75% |
| `malicious` | 246,239 | 10.94% |

Disposition of malicious rows (raw Precinct incident status, see [Ground Truth](#ground-truth-and-disposition)):

`signals`:

| Disposition | Rows |
|---|---|
| `Cold Case` | 3 |
| `Disrupted` | 5,779 |
| `Open` | 15 |
| `Unprocessed` | 1,931 |

`incident_signals`:

| Disposition | Rows |
|---|---|
| `Cold Case` | 14 |
| `Dismissed` | 5 |
| `Disrupted` | 176,510 |
| `Open` | 330 |
| `Unprocessed` | 61,652 |

## Signal columns

Both signal tables share one schema (38 columns).

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | float | Unix epoch seconds. Live rows: Precinct ingest time (artifact timeuuid), seconds after the event. Incident leads: when Precinct's correlation raised the lead, hours to days after the event, at one-second resolution (repaired when invalid or a year off, see `timestamp_source`). Neither is normalised device time; times inside `message_sanitized` are the device's own clock. |
| `event_time` | float | Event time reported by the source product (`starttimeutc`) when available; NaN otherwise. |
| `timestamp_source` | string | Where `timestamp` came from: `artifact.timeuuid`, `lead.observed_at`, `lead.observed_at.year_repaired` |
| `origin` | string | `live` (captured artifact) or `incident_lead` (artifact embedded in an incident) |
| `org_id` | string | Sanitized organization (`ORG-NNNN`) |
| `artifact_id` | string | Precinct artifact timeuuid — join key to `graph/edges.jsonl` (`attrs.artifact_id`). The two signal tables are disjoint on this key: a lead whose live row is in the capture appears in `signals` with `label_binary = malicious`, never in `incident_signals` |
| `message_type` | string | Event classification (e.g., `firewall_action`, `account_logon`, `4624`, `AssumeRole`) |
| `stream_name` | string | Source product/data stream |
| `pipeline` | string | Ingestion pipeline |
| `src_ip`, `dst_ip` | string | Source/destination IP (sanitized) |
| `src_port`, `dst_port` | string | Ports |
| `protocol` | string | Network protocol (6=TCP, 17=UDP, 1=ICMP) |
| `src_host`, `dst_host` | string | Source/destination hostname (sanitized) |
| `username` | string | Associated account (`USER-NNNN`, sanitized; shared with incident credential nodes) |
| `action` | string | Event action (block, permit, logon, logoff) |
| `severity` | string | Severity level |
| `vendor_code` | string | Vendor-specific event code |
| `message_sanitized` | string | Full sanitized raw log message |
| `label_binary` | string | `malicious`, `suspicious`, or `benign` |
| `label_confidence` | float | Confidence in the tier (0.0–1.0). See [Scoring](#scoring). |
| `attack_techniques` | string | JSON array of MITRE ATT&CK technique IDs |
| `attack_tactics` | string | JSON array of MITRE ATT&CK tactic IDs (`TA0001`-style) |
| `defense_techniques` | string | JSON array of MITRE D3FEND technique IDs |
| `mo_name` | string | Modus operandi of the parent incident (e.g., `Data Theft`) |
| `suspicion_score` | float | Precinct incident suspicion score (0.0–1.0); 0 for benign/suspicious |
| `lifecycle_stage` | string | Kill-chain stage (`initial-compromise`, `complete-mission`, ...) |
| `disposition` | string | Raw Precinct incident status (`Disrupted`, `Resolved`, `Dismissed`, `False Positive`, `Cold Case`, `Open`, `Unprocessed`) |
| `disposition_category` | string | `automated` (engine-set status), or an analyst decision: `confirmed-malicious`, `false-positive`, `dismissed` |
| `is_false_positive` | bool | Analyst marked the parent incident a false positive |
| `status_name` | string | Same as `disposition` |
| `incident_ids` | string | JSON array of incident UUIDs (a lead can belong to several incidents) |
| `matched_rules` | string | JSON array of matched WitFoo lead rule descriptions |
| `set_roles` | string | JSON array of WitFoo classification roles (`Exploiting Host`, `C2 Server`, ...) |
| `product_name`, `vendor_name` | string | Security product and vendor |

## Graph data

| Component | Count |
|-----------|-------|
| Nodes | 47,585 (HOST: 36,974, CREDENTIAL: 10,575, SERVICE: 6, FILE: 29, ACTOR: 1) |
| Edges | 1,740,438 |
| User → host edges (`USER_ACTION`) | 692,375 |
| Incident link edges | 335,645 |
| Incidents (per-incident GraphML) | 51,371 |

- **Node ids.** Public IPs are global node ids; private IPs, hostnames and credentials are scoped by organization
  (`ORG-0004/10.44.0.7`, `ORG-0004/user:USER-0007`) because the same private address or account name exists in
  several customer networks. Incident host and credential nodes are mapped onto the same ids (their Precinct uuids are kept in
  `attrs.precinct_node_ids`). Every node carries the same attribute keys; `first_seen`/`last_seen`/`signal_count`
  Other incident node types (`SERVICE`, `FILE`, `ACTOR`, ...) keep their Precinct uuid as node id.
  come from live signals only, `incident_first_observed`/`incident_last_observed` from incident membership.
- **Edges from signals** carry the signal's labels, `attrs.origin`, `attrs.org_id` and `attrs.artifact_id`;
  edge `type` is derived from the message type (`NETWORK_FLOW`, `LOGON`, `AUDIT_EVENT`, ...). A signal with a
  username adds a `USER_ACTION` edge from the credential node to the accessed host (`attrs.host_role` says whether
  that was the destination or the reporting host).
- **Edges from incidents** are `INCIDENT_LINK` with the incident's labels; `timestamp` is the edge's own start time.
- Edge types: `USER_ACTION` (692,375), `AUDIT_EVENT` (336,425), `INCIDENT_LINK` (335,645), `NETWORK_FLOW` (323,376), `EVENT` (45,063), `DNS_RESOLVE` (7,554).
- `graph/graph.graphml` holds the whole merged graph (streaming GraphML).

## Attack reports

`graph/attack_reports.jsonl` holds one natural-language threat-hunting report per incident (51,371),
deterministically composed from the incident's structured metadata (modus operandi, set roles, lead
descriptions, MITRE mappings, timestamps). Each report states that it reflects Precinct's automated correlation
output, not an independent investigation. Derivation:
[`src/precinct6_dataset/attack_reports.py`](https://github.com/witfoo/dataset-from-precinct6/blob/main/src/precinct6_dataset/attack_reports.py).

## Files

- `signals/signals.parquet` — live signals
- `signals/incident_signals.parquet` — embedded incident leads
- `signals/metadata.json` — exact counts, per-label time ranges, org/stream/message-type distributions
- `graph/nodes.jsonl`, `graph/edges.jsonl` — merged provenance graph (NDJSON)
- `graph/incidents.jsonl` — full sanitized incident records with embedded `nodes`, `edges`, `leads` (dicts keyed by
  Precinct uuids, so this file is not exposed as a `load_dataset` config; read it with `pandas.read_json(lines=True)`)
- `graph/incidents_graphml/<x>/<incident_id>.graphml` — one GraphML per incident (sharded by first hex character)
- `graph/attack_reports.jsonl` — attack reports
- `graph/metadata.json` — graph counts and node id scheme
- `reference/lead_rules_catalog.json` — 261 lead detection rules, 158 products, 106 classification sets

## Labeling methodology

**Three-tier labels:**

- **`malicious`** — the event is a triggering signal (lead) of a Precinct incident. In `signals` these are
  live rows joined to their incident on `artifact_id`; in `incident_signals` they are the embedded copies of
  leads whose live rows fall outside the capture.
- **`suspicious`** — the event matched one or more of WitFoo's 261 lead detection rules but is not a lead of any
  incident.
- **`benign`** — no rule matched and the event is not part of any incident.

A lead that belongs to several incidents is one row whose `incident_ids` lists them all; its `mo_name`,
`disposition` and `suspicion_score` come from the highest-suspicion incident.

### Ground truth and disposition

**All labels derive from WitFoo Precinct's automated incident correlation engine — there is no independent,
analyst-verified ground truth.** Treat Precinct as a strong but imperfect oracle. `disposition` is the parent
incident's Precinct status, and most statuses are set by the engine, not by an analyst:

| `disposition` | Set by | `disposition_category` |
|---|---|---|
| `Unprocessed` | Engine: correlated into an incident, never analyzed | `automated` |
| `Disrupted` | Engine: verdict after one analysis pass (not an analyst confirmation) | `automated` |
| `Open` | Engine: still being re-analyzed, no decision | `automated` |
| `Cold Case` | Engine: aged out after repeated analysis | `automated` |
| `Resolved` / `Confirmed` / `Investigating` | Analyst | `confirmed-malicious` |
| `Dismissed` | Analyst | `dismissed` |
| `False Positive` | Analyst | `false-positive` |

Analyst-set statuses are rare, so `disposition` is not a usable ground-truth signal on its own; check the
`disposition_distribution` in `signal/metadata.json` for how many rows carry each status.

### Scoring

- **`suspicion_score`** — Precinct's proprietary score of the parent incident (0–1). Zero for benign and suspicious.
- **`label_confidence`** — how much corroborating evidence supports the tier (not a probability of maliciousness):

  | Label | Formula |
  |---|---|
  | `malicious` | `max(0.6, suspicion_score)` clamped to 0.95; 0.3 if `is_false_positive` |
  | `suspicious` | `0.4 + 0.1 × n_matched_rules + 0.05 × n_set_roles`, clamped to [0.5, 0.85] |
  | `benign` | `0.5` |

### MITRE ATT&CK mappings

Tactics and techniques are derived from (1) WitFoo set role names on the incident, (2) the incident's modus
operandi, and (3) per-product framework data embedded in `incident.nodes.products.frameworks`, deduplicated.
They are priors, not analyst-confirmed per-event attributions. Mapping tables:
[`src/precinct6_dataset/mitre_mapping.py`](https://github.com/witfoo/dataset-from-precinct6/blob/main/src/precinct6_dataset/mitre_mapping.py).

## Source products

The events in **this build** come from **19 security products** across **12 vendors**
(exact counts in `signals/metadata.json` under `product_distribution` / `vendor_distribution`).

Most frequent products: AWS Instance Backup, Windows Active Directory, Windows Logs, VMWare VCenter, ASA Firewall, AWS VPC Security, Barracuda WAF, Linux PAM, ManageEngine ADManager, Graph, Barracuda ESS, Falcon, Cisco Network Operating System, Apache Web Server.
Vendors: Microsoft, Amazon Web Services, VMWare, Cisco, Barracuda, Linux, ManageEngine, Crowdstrike, Apache, Symantec, SentinelOne, WitFoo.

The generator's rule catalog (`reference/lead_rules_catalog.json`) covers a much wider set —
158 products across firewalls, endpoint protection, network detection, identity, cloud,
email security and infrastructure — because it is shared by every deployment; only the products above
actually appear in this capture.

Top streams in this build: `aws_cloudtrail_events` (543,159), `microsoft-windows-security-auditing` (421,587), `windows_security_audit` (336,425), `vcenter` (266,201), `java_stack_trace` (154,465), `cisco_asa` (95,143), `no_useful_info` (48,246), `aws_cloud_trail` (34,484), `dnsmasq` (34,110), `aws_vpc_flow_log` (19,219).

## Sanitization

All customer-identifying information was removed with the open-source four-layer pipeline
([`witfoo/dataset-from-precinct6`](https://github.com/witfoo/dataset-from-precinct6)):

1. **Structured field sanitization + Aho-Corasick multi-pattern sweep** — deterministic tokens (public IPs →
   [RFC 5737](https://datatracker.ietf.org/doc/html/rfc5737) TEST-NET, private IPs → HMAC-remapped RFC 1918,
   hostnames → `HOST-NNNN`, accounts → `USER-NNNN`, organizations → `ORG-NNNN`, emails → `user-NNNN@example.net`,
   SIDs, AWS accounts/ARNs, machine accounts), then a sweep over every string field with the full registry.
   Record identifiers (artifact/incident uuids) are protected from the sweep.
2. **Format-specific log parsing** — Cisco ASA, Windows Security XML, WinLogBeat, AWS CloudTrail, Palo Alto,
   VMware vCenter, DNS, and a generic fallback.
3. **ML residual detection** — Microsoft Presidio (spaCy) and BERT NER on a stratified sample; findings trigger
   full re-sanitization.
4. **LLM contextual review** — sampled review by the local WitQ model (ran for this build: 1,500 records reviewed by `witq`, 2 additional values registered). The ML layer (3) sampled 3,000 records and registered 470 additional values.

The same original value always maps to the same token across both signal tables, the incidents and the graph,
so topology and identity are preserved. Both dataset sizes were produced from one registry, so tokens agree
between them. The registry for this build holds 85,088 mappings.

## Research context

Produced in collaboration with the University of Canterbury (New Zealand) Computer Science and Software
Engineering department for two research projects: an **AI cyber-security battle simulator** (improving CybORG
with realistic IDS observations and graph-based defense policies) and **intrusion detection based on provenance
graphs** (evaluating KnowHow, NodLink and similar PIDS).

## Limitations

- **Label imbalance** reflects production SOC reality; sample accordingly.
- **Temporal scope**: the live capture spans 2024-07-26 11:10:23 UTC to 2024-08-01 06:00:03 UTC with uneven
  per-organization coverage; incident leads span 2022-05-30 14:43:45 UTC to 2024-07-28 16:39:47 UTC.
- **Ground truth**: labels are Precinct's automated correlation; stratify with `disposition`.
- **Sanitization trade-offs**: some free-text detail is reduced by PII replacement.
- **Tokens differ from v1**: the v2 registry was rebuilt, so `USER-NNNN` / `HOST-NNNN` / `ORG-NNNN` values do not
  correspond to v1 values.

## Citation

```bibtex
@dataset{witfoo_precinct6_2026,
  title={WitFoo Precinct6 Cybersecurity Dataset},
  author={WitFoo, Inc.},
  year={2026},
  version={2.1.0},
  url={https://huggingface.co/datasets/witfoo/precinct6-cybersecurity},
  license={Apache-2.0}
}
```

## License

[Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)
