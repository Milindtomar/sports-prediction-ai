# HCI study protocol (draft – not yet run)

**Status: no human-participant data have been collected.** This protocol must be approved by the relevant course/institution before any real participant is recruited. This project does not claim ethics approval.

## 1 Research question
Compared with a prediction-only dashboard, how does an interactive and explainable sports-analytics interface affect decision accuracy, task time, confidence, perceived trust in AI and perceived usability? Hypotheses H1–H4 are listed in the paper (§3) and are untested.

## 2 Design
- Between-subjects: Interface A (prediction + probability only) vs Interface B (prediction + "Why?" explanation + what-if simulation + momentum).
- Assignment: alternates A, B, A, B by session count (balanced groups). Task order rotated per participant (`session.id mod 5`); position stored per task.
- Same model, same scenarios in both conditions.

## 3 Participants (suggested)
- Target: at least 10 per group for a student project (the analysis script refuses inferential statistics below 5 per group). No power claim.
- Adults who consent; sports familiarity recorded on a 3-level self-report (none / some / expert).
- Recruit only through channels approved for the study. Do not collect names, emails, student IDs or locations.

## 4 Materials
Running app (`start.bat` / `start.sh`), HCI Study page, five tasks (paper Appendix A), SUS (10 items), four study-specific trust items (Appendix B; not validated), optional comment box (≤500 chars).

## 5 Procedure (≈10–15 min)
1. Read the consent text; tick the consent box (the session cannot start otherwise). Voluntary participation and the right to withdraw at any time are stated on screen.
2. Enter an anonymous code (letters/digits/space/_/./-), choose familiarity.
3. System assigns the interface. Five tasks, each with answer, confidence (1–7), trust (1–7).
4. SUS + four trust items + optional comment.
5. Debrief: all data are model output on synthetic matches; nothing is a real forecast.

## 6 Measures
Decision accuracy (server-graded against ground truth derived from the pipeline); task time (ms); confidence; single-item trust; interaction count; SUS (0–100); trust-scale mean (1–7).

## 7 Withdrawal and data handling
A participant may stop at any time. To remove a session after the fact the participant quotes their anonymous code to the researcher, who deletes the rows from the database. Exports are CSV/JSON with formula-injection neutralised. Keep exports on approved storage; do not publish raw data without consent.

## 8 Analysis plan
Unit = participant. Run `python scripts/analyze_hci.py data/hci_export.csv`. It reports descriptives, Welch t, Mann–Whitney U, Cohen's d with bootstrap CI, and Fisher's test for accuracy. It prints no statistics for empty data or groups under the minimum. Report effect sizes with intervals; treat p-values as exploratory (five measures, small n). `--demo` produces clearly labelled SIMULATED data and must never be reported.

## 9 Known limitations
Bundle effect (B differs in several ways from A); synthetic scenarios; small samples; novelty effects; trust items unvalidated.
