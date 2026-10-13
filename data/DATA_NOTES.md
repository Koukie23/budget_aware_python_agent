# MBPP data notes

## Raw files (`data/raw/`)

Downloaded byte-for-byte from the official repository with `curl`. Do not re-fetch through a web-to-markdown tool: it collapses indentation and corrupts the reference code.

| File | Source | SHA-256 |
| --- | --- | --- |
| `mbpp.jsonl` | `google-research/mbpp/mbpp.jsonl` | `ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f` |
| `sanitized-mbpp.json` | `google-research/mbpp/sanitized-mbpp.json` | `ca95deaa9a01ef0a6f439f88bcf0dd3db3563d22f22aad6cae04ebb9a8d8c8e9` |

License: CC-BY-4.0. Paper: Austin et al., 2021.

## Official fields

| Corpus | Fields |
| --- | --- |
| Full (974) | `task_id`, `text`, `code`, `test_list`, `test_setup_code`, `challenge_test_list` |
| Sanitized (427) | `source_file`, `task_id`, `prompt`, `code`, `test_imports`, `test_list` |

Most problems have 3 asserts. Only 11 full problems have `challenge_test_list`; sanitized has none.

## Splits by task_id (official README)

| task_id | split | full | sanitized |
| --- | --- | --- | --- |
| 1-10 | prompt (few-shot only) | 10 | 7 |
| 11-510 | test | 500 | 257 |
| 511-600 | validation | 90 | 43 |
| 601-974 | train | 374 | 120 |

Both corpora share `task_id`, so splitting by ID range keeps each problem in the same split everywhere.

## Verification (`scripts/build_t1_samples.py`)

- Sanitized: 0 parse failures; every reference solution passes its own tests.
- Full: 0 parse failures; 2 reference solutions fail their own tests, both in the test split and both caused by exact float equality:
  - 180 `distance_lat_long`
  - 493 `calculate_polygons`
  How to handle them is decided in T4.

## T1 sample fields (`data/samples/t1_samples.jsonl`)

Aligned with plan section 6.2. `prompt` is added in T4 once the template is fixed.

| Field | Meaning |
| --- | --- |
| `task_id`, `source`, `split` | Official id, corpus, split from ID range |
| `requirement` | Sanitized `prompt` text |
| `function_name`, `function_signature` | First top-level `def` in the reference code |
| `target_code` | Reference solution (training target) |
| `feedback_tests` | Official `test_list`, visible to the agent |
| `hidden_tests` | Empty until the hidden-test source is decided in T4 |
| `test_imports` | Extra imports required by tests |
| `reference_test_results` | Result of running `target_code` on `feedback_tests` |

T1 samples: 2 (prompt), 12 (test), 555 (validation), 604 (train). They are for interface checks and UI demos only; they are not used to tune anything.

## Commands

```bash
python scripts/build_t1_samples.py
python scripts/validate_sample.py --task-id 2
```
