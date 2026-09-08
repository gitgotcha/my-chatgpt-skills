# Behavior Scenarios

## copy-only

Input: change one settings-page button label with no behavior change.
Expected: `light`; reviewer `gpt-5.6-luna` with `low` reasoning; deterministic visual/copy checks are inputs and no deep-model call is needed. A model-free waiver is allowed only when the acceptance is fully mechanical and reviewer judgment adds no value.

## bounded-csv-export

Input: add CSV export to one module with known fields and authorization rules.
Expected: `standard`; one post-implementation review by a verified standard-capable model; check field mapping, quoting, encoding, and authorization.

## tenant-isolation

Input: add a missing `tenant_id` predicate in a one-line query patch.
Expected: `critical` despite the small diff; pre-implementation review of isolation and regression design, then post-implementation review of the exact diff and cross-tenant test evidence.

## outbox-transaction

Input: change the transaction boundary between order persistence and outbox insertion.
Expected: `critical`; pre-implementation review checks atomicity, retries, and duplicate-event design; post-implementation review checks source and failure-path evidence.

## missing-model-inventory

Input: the plan will run on an environment whose available model IDs and controls cannot be verified.
Expected: author all other plan details; use `model: null`, `status: blocked_model_config`, and list required metadata. Do not copy the current author's model list.

## existing-plan-change

Input: revise one task in a plan with recorded completed reviews elsewhere.
Expected: reset reviews affected by the changed task or input version to `pending`; preserve unrelated completed reviews only when their scope, version, and evidence remain applicable.
