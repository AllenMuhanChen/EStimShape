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

- **Phase 0 (this folder): `live_spike_marker_probe.py`** — standalone probe that
  proves live spikes + marker timing against the real rig. No dependency on the
  (abandoned) `intan/companion` app; only numpy/scipy. Validates the RHX TCP frame
  layout empirically.
- **Phase 1** — "controlled presentation" mode + per-presentation trial capture to
  the DB (stim snapshot, position, depth, epoch, per-channel spike count/rate).
  Wire the RF experiment to start RHX recording (`set runmode record`) like the
  other experiments.
- **Phase 2** — orientation tuning view (mean rate ± SEM vs. orientation).
- **Phase 3** — response-weighted RF heatmap (stimulus shadow × rate, accumulated).
- **Phase 4** — matchstick color tuning; polish.

## Running Phase 0

In Intan RHX: `Network -> Remote TCP Control`, open Command (5000) and Waveform
(5001) outputs and click Listen (status "Pending").

```
python live_spike_marker_probe.py --channels A-000 --marker-bit 1
```

Then flash the stimulus (or wave something past the photodiode). Expect `MARKER
ON/OFF` lines with epoch durations and the spike count inside each epoch, plus a
periodic live spike-rate readout.

### Things Phase 0 exists to confirm on the rig
- Exact digital-in enable command (`--digital-enable-cmd`, default
  `set digitalin.tcpdataoutputenabled true`).
- The digital-in **frame byte layout** — the probe auto-detects block size and
  aborts loudly on mismatch rather than reporting garbage. Use `--dump-frame`.
- Which digital bit is the marker (`--marker-bit`, default 1 = DIGITAL-IN-2).
- Response-latency window offsets (`--left-ms`, `--right-ms`).
