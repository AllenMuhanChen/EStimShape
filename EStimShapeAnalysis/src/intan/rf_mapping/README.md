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
  other experiments. **Data model in place:** `RFMappingResponse` (one row per
  presentation x neural channel) — DDL in
  `sql_queries/create_rf_mapping_response_table.sql`; create it from the IDE by
  running `create_rf_mapping_table.py` (targets the current session's ga
  database; edit `TARGET_DB` to also create it in the template).
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
- an **Aux fields** row (the enabled digital/analog channels) that flags which
  field is *changing* — flash the stimulus and the marker field lights up,
- a MARKER ON/OFF indicator,
- an event log with each epoch's duration and the spike count inside it,
- a **Dump one frame** button for inspecting the raw stream layout.

### Discovering the marker (the point of Phase 0)
The probe does **not** assume the frame layout. It measures the true frame size
from the stream (distance between magic numbers), derives how many extra 2-byte
"aux" fields are present (your enabled digital-in / analog-in channels), and
parses them. Spikes stream regardless.

To find the marker:
1. In the **Extra channel enable** box, add the command(s) that enable your
   photodiode line for TCP output (one per line). The digital-in native name
   varies by RHX build — check RHX's *Data Output* tab. Try `DIGITAL-IN-01`,
   `DIGITAL-IN-1`, or `ANALOG-IN-1` if the photodiode is on an ADC. On the
   observed rig (`ControllerStimRecord`, RHS), `set digitalin.tcpdataoutputenabled
   true` added nothing — this box is how you iterate to the right name.
2. Start, then flash the stimulus. The **Aux fields** row marks the changing
   field `*changing*`. Set **Marker aux index** to that field's index.
3. **Marker bit** = `-1` treats any nonzero value as ON (per-line digital, the
   usual case). If a field carries the full 16-bit digital word instead, set the
   bit number.
4. Tune **latency left/right ms** for the response window used to count spikes.
