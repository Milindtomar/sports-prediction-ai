# HCI study module

## Research question

Does an **explainable, interactive** prediction interface (B) improve understanding, decision quality and calibrated trust compared with a **probability-only** interface (A)?

## Design

Between-subjects. Each participant sees one interface for all five tasks. Assignment alternates A, B, A, B… (balanced); "Force A/B" exists for demos only. Task order is rotated per participant (`session.id mod 5`, a simple Latin-square rotation) and each answer stores its `position`, so order effects can be checked.

| | Interface A | Interface B |
|---|---|---|
| Content | scoreboard + win probability | A + a "Why?" panel (helping / hurting factors) + a "Simulate" panel that calls the real what-if API |

## Tasks (ground truth from the real pipeline)

| ID | Sport | Task | Ground truth |
|---|---|---|---|
| T1 | Cricket | Which side is favoured? | Side with p ≥ 55%; "too close" if 45–55% |
| T2 | Cricket | Which factor most influences the prediction? | Largest-|Shapley| feature |
| T3 | Cricket | Which event would increase the batting side's win probability most? | Max of the event sweep |
| T4 | Basketball | Which event would reduce the home team's win probability most? | Min of the event sweep |
| T5 | Football | Main driver of the home-win probability? | Largest-|Shapley| feature |

Ground truth is computed on the server when a result is submitted; it is never sent to the browser with the task. The task states are fixed in `backend/app/services/hci.py`.

## Measures

Task time (ms, from task display to submit), decision accuracy (vs ground truth), confidence (1–7), trust in the AI prediction (1–7), number of interactions (Why? toggles and simulations), the 10-item **System Usability Scale** (standard scoring: odd items x−1, even items 5−x, sum × 2.5), four **study-specific trust items** (1–7; explicitly *not* a validated scale) and an optional free-text comment (≤ 500 chars).

## Analysis

`GET /api/hci/results` returns per-group means/SDs, per-task accuracy, and tests of B vs A: Welch t-test (time, confidence, trust, SUS; Cohen's d reported) and Fisher exact test (accuracy). With small samples treat p-values as indicative; the endpoint also returns a note to that effect. `GET /api/hci/export.csv` and `/api/hci/export.json` export every task result (cells starting with `=`, `+`, `-`, `@` are prefixed with `'`). For a participant-level analysis run `python scripts/analyze_hci.py export.csv`: Welch t, Mann–Whitney U, Cohen's d with a bootstrap CI, Fisher for accuracy. It prints no statistics for empty data or groups smaller than `--min-per-group` (default 5). `--demo` uses SIMULATED rows with a banner and must never be reported as a finding. Full protocol: `research/hci_protocol.md`.

## Data and ethics

* **No data is pre-filled or fabricated.** The Results tab shows an empty state until participants finish tasks. (All automated test sessions were deleted from the shipped database.)
* A consent text and voluntary-withdrawal notice are shown first; a session cannot start without ticking consent (`consented` is stored). Only an anonymous code (letters, digits, space, `_ . -`; no names), experience level and responses are stored. The app does **not** claim ethics approval; obtain institutional approval before a real study. There is no authentication.
* Limitations: five tasks only, fictional teams, synthetic model, interface differences are confounded (B has more content and more to do), and "interactions" are only counted in B.

## Running a session

1. Open **HCI Study → Run study**, enter a participant code, choose *Auto*.
2. Participant completes five tasks, then the SUS.
3. Review **Results**, download the CSV.
