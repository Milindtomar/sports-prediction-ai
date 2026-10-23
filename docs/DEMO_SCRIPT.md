# Demo script (5–7 minutes)

Start the app (`start.bat` on Windows, `./start.sh` elsewhere) and open <http://localhost:5173>. Everything shown is **synthetic**; say so in the first sentence.

| Min | Screen | Say / do | Point to prove |
|---|---|---|---|
| 0:00 | **Landing** | "Predictions usually show a number and nothing else. Here you can ask why and what-if." Note the *SYNTHETIC DEMO DATA* badge. Click **SIX** in the live box. | The % changes by a computed amount; the note says it calls the real model. |
| 0:45 | **Enter Analytics → Sport selection** | Point at the per-sport model status and "Demo data" label. Pick Cricket. | Honest labelling; three sports share one UI. |
| 1:30 | **Match Center** | Scrub the timeline; show win probability with its model-range band and the momentum factors. Open **Why?** | Explanation items add up to the prediction (additivity). |
| 2:45 | **Simulation Lab** (link from Match Center) | Apply *Wicket*, then *Six*. Read the attribution table. Run the event sweep. | Features are recomputed and the same model is re-run; attribution sums to the change. |
| 4:00 | **AI Analytics / Player Lab** | Show the AI-assisted recommendation wording and a player's PREDICTION vs ACTUAL RESULT history with ranges. | Labelled as AI-assisted; weak targets show wide ranges. |
| 5:00 | **Model Insights** | Metrics table, calibration, confusion matrix, model/dataset version and seed. | Numbers come from `metrics.json`; synthetic caveat shown. |
| 5:45 | **HCI Study** | Show consent text and anonymous code. Run one task in Interface B, then the Results tab. | "Participants: 1 – no tests are shown, and none are invented." |
| 6:30 | Close | State limits: synthetic data, no human results yet, Windows scripts and cloud deploy files untested. | Candour. |

**Backup if the API is slow:** the pages show an error with a Retry button. Restart with the launcher; models load in about 2 s.
**Before a real study session:** delete demo/test HCI sessions (`rm backend/sportsai.db` and restart re-seeds only matches and players).
