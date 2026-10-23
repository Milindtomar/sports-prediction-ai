# AI poster-generation prompt (self-contained)

Paste everything below the line into an AI image/design tool or give it to a designer. It does not depend on any other file.

---

Design a single academic research poster, A1 portrait, 3 columns, light background, large legible sans-serif type (Inter or similar), generous white space, readable from 1.5 m. Use one consistent accent colour per sport: cricket green, football blue, basketball orange. Flat vector style; no stock photos, no photographs of real people, no real team/league logos.

**Strict honesty constraints:** use ONLY the text and numbers below. Do not invent results, participants, quotes, logos or institution marks. Every machine-learning number must be labelled "synthetic benchmark". State clearly that the human study is proposed and that no human-participant results exist yet. Leave author/institution/email as placeholders in square brackets, and leave a QR placeholder box labelled [QR].

**Figures to place (provided separately as images):** system architecture diagram; ML pipeline diagram; calibration/model-comparison chart; screenshot of the match-analytics screen (with the "SYNTHETIC DEMO DATA" badge visible); HCI conditions diagram; study-flow diagram. If images are not available, draw simple labelled boxes-and-arrows placeholders.

**Content (verbatim):**


**Title:** Designing an Explainable and Interactive Sports Analytics Interface
**Subtitle:** A synthetic-data prototype and HCI evaluation framework
**Authors:** [Author name(s)] · [Institution] · [Email]

## Problem
A win probability like "62%" is easy to read and hard to question. Do explanations and what-if tools help people understand it?

## What we built
Cricket, football and basketball analytics with calibrated win probability, "why this prediction?" explanations (Shapley-style, probability scale), a momentum heuristic, a what-if lab that re-runs the model, and an HCI study module.

## Synthetic benchmark results (test split)
| | Cricket | Football | Basketball |
|---|---|---|---|
| Model | Logistic reg. | Logistic reg. | Logistic reg. |
| Accuracy | 0.696 | 0.633 | 0.787 |
| ROC-AUC | 0.774 | 0.802 | 0.882 |
| Log-loss | 0.564 | 0.790 | 0.416 |
| ECE | 0.019 | 0.018 | 0.021 |

*All data are synthetic simulator output. These numbers show the pipeline works; they are not real-world forecasting skill.*

## Method highlights
Chronological, match-grouped 70/15/15 splits · pre-match ratings updated only after each match · simplest model within 1% of best · calibration checked · 12-model bootstrap band (model uncertainty only).

## HCI study (proposed)
Between-subjects: A = prediction only, B = prediction + explanation + what-if. Five tasks with server-computed ground truth. Measures: accuracy, time, confidence, trust, SUS. **No human-participant results have been collected yet.**

## Hypotheses (untested)
H1 higher accuracy with B · H2 better identification of the main factor · H3 possible gains in confidence/usability · H4 what-if helps reasoning but may add time.

## Limitations
Synthetic data · linear models win because simulators are near log-linear · heuristic momentum · small planned samples · bundle effect (explanation + interactivity).

## Next steps
Run the approved study · retrain on licensed real data · validate the recommendation component · factorial design.

## References (verified subset)
Štrumbelj & Kononenko 2014 · Miller 2019 · Doshi-Velez & Kim 2017 · Lundberg & Lee 2017 · Brier 1950 · Niculescu-Mizil & Caruana 2005.


**Layout:** Title banner across the top. Column 1: Problem, What we built, architecture figure. Column 2: Method highlights with pipeline figure, synthetic benchmark table, calibration chart, explanation screenshot. Column 3: HCI study with two figures, hypotheses (labelled untested), limitations, next steps, references, contact placeholders. Keep each text block under 60 words where possible.
