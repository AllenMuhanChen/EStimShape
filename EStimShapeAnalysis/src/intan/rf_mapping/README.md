# RF-Plotter live tuning (Intan RHX)

Live neural feedback inside the RF Plotter: stream spikes from Intan RHX over TCP,
align them to the photodiode marker, and build tuning curves / RF maps from
controlled stimulus presentations.

## Design summary

- **Controlled-presentation paradigm.** Stimulus properties are frozen during a
  presentation; you flash it on/off (F key) and adjust only between flashes. Each
  marker epoch is therefore an unambiguous response to one known stimulus — no
  need to revamp the marker channel to encode stimulus identity.
- **Timing ground truth = the photodiode marker.** Spikes and the marker arrive on
  the same Intan sample clock (same TCP stream), so alignment is exact.
- **Modes are just views over logged trials:** orientation tuning, response-weighted
  RF heatmap, color (matchstick) tuning.

## Phases

- **Phase 0 (this folder): `live_spike_marker_probe.py`** — a small **GUI** probe
  (Tkinter, no command line) that proves live spikes + marker timing against the
  real rig. No dependency on the (abandoned) `intan/companion` app; GUI is stdlib
  Tkinter, only numpy/scipy needed for detection. Validates the RHX TCP frame
  layout empirically.
- **Phase 1** — "controlled presentation" mode + per-presentation trial capture to
  the DB (stim snapshot, position, depth, epoch, per-channel spike count/rate).
  Wire the RF experiment to start RHX recording (`set runmode record`) like the
  other experiments.
- **Phase 2** — orientation tuning view (mean rate ± SEM vs. orientation).
- **Phase 3** — response-weighted RF heatmap (stimulus shadow × rate, accumulated).
- **Phase 4** — matchstick color tuning; polish.

## Running Phase 0 (GUI — no command line)

In Intan RHX: `Network -> Remote TCP Control`, open Command (5000) and Waveform
(5001) outputs and click Listen (status "Pending").

Then just open `live_spike_marker_probe.py` in your IDE and click **Run** (or
double-click it) — a window opens. Fill in host / channels / marker bit, click
**Start**, and flash the stimulus (or wave something past the photodiode).

The window shows:
- a live per-channel spike-rate readout and rolling plot,
- a MARKER ON/OFF indicator,
- an event log with each epoch's duration and the spike count inside it,
- a **Dump one frame** button for inspecting the raw stream layout.

### Things Phase 0 exists to confirm on the rig (all editable fields in the window)
- Exact digital-in enable command (default `set digitalin.tcpdataoutputenabled true`).
- The digital-in **frame byte layout** — the probe auto-detects block size and
  reports a loud mismatch in the log rather than showing garbage; use **Dump one
  frame**.
- Which digital bit is the marker (default bit 1 = DIGITAL-IN-2).
- Response-latency window offsets (latency left/right ms).
