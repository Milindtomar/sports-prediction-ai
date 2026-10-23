# Poster content (ready to paste)

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
