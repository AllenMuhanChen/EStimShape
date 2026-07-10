#!/usr/bin/env python3
"""
Phase 0 — Live Spike + Marker Probe (Intan RHX)
===============================================
A small GUI (Tkinter, no command line) that de-risks the RF-Plotter live-tuning
feature. It proves, against your actual rig, that we can:

  1. Stream amplifier data live from RHX over TCP and detect spikes (per channel).
  2. Read the photodiode MARKER (a digital-in bit) on the SAME stream, so spikes
     and stim on/off share Intan's sample clock and align exactly.
  3. Show the spike count that falls inside each marker epoch — the exact
     measurement Phase 1 will log per stimulus presentation.

Run it by opening this file in your IDE and clicking Run (no terminal, no
arguments). A window opens; type in the connection settings and click Connect,
then Start. It is SELF-CONTAINED: own sockets, spike detection inlined, and NO
dependency on the (abandoned) companion app. Only numpy/scipy are required
(both already used across the analysis code); the GUI is stdlib Tkinter.

--------------------------------------------------------------------------------
RHX setup (in the Intan RHX software first)
--------------------------------------------------------------------------------
  Network -> Remote TCP Control:
    * Command Output   : <host> : 5000  -> Listen  (status "Pending")
    * Waveform Output  : <host> : 5001  -> Listen  (status "Pending")
  (The Spike port is NOT used by this probe.)

You do NOT need to pre-enable channels; the probe enables exactly the channels
you type in (WIDE band) plus the digital inputs.

--------------------------------------------------------------------------------
THINGS THIS PROBE EXISTS TO CONFIRM ON THE RIG
--------------------------------------------------------------------------------
  * Digital-in enable command (editable field, default
    'set digitalin.tcpdataoutputenabled true').
  * Frame layout: the probe AUTO-DETECTS block size from the stream (distance
    between magic numbers) and checks it against the expected frame size. On
    mismatch it reports loudly in the log instead of showing garbage. Use the
    "Dump one frame" button to inspect the raw layout.
  * Marker bit: "marker channel 2" is assumed to be DIGITAL-IN-2 == bit 1
    (0-based). Change the field if it's wired elsewhere.
"""

import queue
import socket
import struct
import threading
import time
from collections import deque

import numpy as np

try:
    from scipy.signal import butter, sosfilt
    _HAVE_SCIPY = True
except Exception:  # pragma: no cover - scipy expected on the rig
    _HAVE_SCIPY = False


# ── RHX protocol constants (from IntanRHX_TCPDocumentation.pdf v3.x) ──────────
MAGIC_NUMBER = 0x2EF07A08
FRAMES_PER_BLOCK = 128           # RHX always frames data in blocks of 128
COMMAND_BUFFER_SIZE = 4096
MICROVOLTS_PER_BIT = 0.195
SAMPLE_OFFSET = 32768
BYTES_TIMESTAMP = 4              # int32 sample index, per frame
BYTES_PER_AMP_SAMPLE = 2         # uint16 per amplifier channel per band
BYTES_DIGITAL_WORD = 2           # uint16 digital-in word, per frame (if enabled)


# ── Command socket ───────────────────────────────────────────────────────────
class RHXCommandClient:
    """Text command socket to RHX (get/set/execute)."""

    def __init__(self, host, port, timeout=5.0):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect((host, port))

    def _send(self, text):
        self.sock.sendall(text.encode("utf-8"))
        time.sleep(0.02)  # let RHX process before we read/next command
        try:
            return self.sock.recv(COMMAND_BUFFER_SIZE).decode("utf-8").strip()
        except socket.timeout:
            return ""

    def get(self, param):
        resp = self._send(f"get {param}")
        if resp.startswith("Return:"):
            parts = resp.split()
            if len(parts) >= 3:
                return " ".join(parts[2:])
            if len(parts) == 2:
                return parts[1]
        return resp

    def set(self, param, value):
        return self._send(f"set {param} {value}")

    def execute(self, action):
        return self._send(f"execute {action}")

    def get_sample_rate(self):
        return float(self.get("sampleratehertz"))

    def set_runmode(self, mode):
        # mode in {"stop", "run", "record"}
        return self.set("runmode", mode)

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


# ── Waveform socket + block parsing ──────────────────────────────────────────
class WaveformStream:
    """
    Reads RHX waveform blocks and parses each frame as:
        [int32 timestamp][uint16 * n_channels (WIDE band)][uint16 digital word?]

    Maintains a byte buffer across reads so partial blocks are handled.
    """

    def __init__(self, host, port, n_channels, has_digital, timeout=5.0):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect((host, port))
        self.n_channels = n_channels
        self.has_digital = has_digital
        self._buf = bytearray()

        self.bytes_per_frame = (
            BYTES_TIMESTAMP
            + n_channels * BYTES_PER_AMP_SAMPLE
            + (BYTES_DIGITAL_WORD if has_digital else 0)
        )
        self.bytes_per_block = 4 + FRAMES_PER_BLOCK * self.bytes_per_frame

    def flush(self):
        """Discard queued bytes (stale data from before we started)."""
        self.sock.setblocking(False)
        try:
            while True:
                chunk = self.sock.recv(65536)
                if not chunk:
                    break
        except (BlockingIOError, socket.error):
            pass
        finally:
            self.sock.setblocking(True)
        self._buf = bytearray()

    def _recv_available(self):
        """Read whatever is currently available into the buffer."""
        self.sock.setblocking(False)
        got = 0
        try:
            while True:
                chunk = self.sock.recv(65536)
                if not chunk:
                    break
                self._buf.extend(chunk)
                got += len(chunk)
        except (BlockingIOError, socket.error):
            pass
        finally:
            self.sock.setblocking(True)
        return got

    def detect_block_size(self, settle_sec=0.5):
        """
        Empirically determine bytes-per-block from the live stream by measuring
        the byte distance between two consecutive magic numbers. Returns the
        detected block size, or None if it couldn't be determined.
        """
        deadline = time.time() + settle_sec
        while time.time() < deadline:
            self._recv_available()
            time.sleep(0.05)
        data = bytes(self._buf)
        magic = struct.pack("<I", MAGIC_NUMBER)
        first = data.find(magic)
        if first < 0:
            return None
        second = data.find(magic, first + 1)
        if second < 0:
            return None
        return second - first

    def read_frames(self):
        """
        Pull all currently-available complete blocks. Returns
        (timestamps, amp_uV, digital) where:
            timestamps : int32 array, one per frame
            amp_uV     : float array (n_channels, n_frames), microvolts
            digital    : uint16 array (n_frames,) or None
        Returns None if no complete block is available yet.
        """
        self._recv_available()
        if len(self._buf) < self.bytes_per_block:
            return None

        n_blocks = len(self._buf) // self.bytes_per_block
        usable = n_blocks * self.bytes_per_block
        raw = bytes(self._buf[:usable])
        del self._buf[:usable]

        total_frames = n_blocks * FRAMES_PER_BLOCK
        timestamps = np.empty(total_frames, dtype=np.int32)
        amp = np.empty((self.n_channels, total_frames), dtype=np.float64)
        digital = np.empty(total_frames, dtype=np.uint16) if self.has_digital else None

        idx = 0
        f = 0
        for _ in range(n_blocks):
            magic = struct.unpack_from("<I", raw, idx)[0]
            idx += 4
            if magic != MAGIC_NUMBER:
                raise ValueError(
                    f"Frame desync: expected magic 0x{MAGIC_NUMBER:08x}, got "
                    f"0x{magic:08x}. The frame layout assumption is wrong "
                    f"(bytes_per_frame={self.bytes_per_frame})."
                )
            for _ in range(FRAMES_PER_BLOCK):
                timestamps[f] = struct.unpack_from("<i", raw, idx)[0]
                idx += 4
                for ch in range(self.n_channels):
                    raw_sample = struct.unpack_from("<H", raw, idx)[0]
                    idx += 2
                    amp[ch, f] = MICROVOLTS_PER_BIT * (raw_sample - SAMPLE_OFFSET)
                if self.has_digital:
                    digital[f] = struct.unpack_from("<H", raw, idx)[0]
                    idx += 2
                f += 1

        return timestamps, amp, digital

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


# ── Spike detection (inlined; mirrors lfp/mua_detection.py) ───────────────────
def detect_spikes(wideband, sample_rate, highpass_hz=300.0,
                  threshold_rms=4.0, refractory_sec=0.001):
    """
    -N x RMS threshold MUA detection. Returns sample indices of spikes.
    Kept identical in spirit to the offline detector so live/offline agree.
    """
    if _HAVE_SCIPY:
        nyq = sample_rate / 2.0
        sos = butter(4, highpass_hz / nyq, btype="high", output="sos")
        filtered = sosfilt(sos, wideband)
    else:
        # Fallback: crude first-difference high-pass if scipy is missing.
        filtered = np.diff(wideband, prepend=wideband[0])

    rms = np.sqrt(np.mean(filtered ** 2))
    if rms == 0:
        return np.array([], dtype=int)
    threshold = -threshold_rms * rms

    below = filtered < threshold
    crossings = np.where(np.diff(below.astype(np.int8)) == 1)[0] + 1
    if len(crossings) == 0:
        return np.array([], dtype=int)

    refractory = max(1, int(refractory_sec * sample_rate))
    n = len(filtered)
    spikes = []
    for c in crossings:
        end = min(c + refractory, n)
        spikes.append(c + int(np.argmin(filtered[c:end])))
    spikes = np.array(spikes, dtype=int)

    kept = [spikes[0]]
    for s in spikes[1:]:
        if s - kept[-1] >= refractory:
            kept.append(s)
    return np.array(kept, dtype=int)


# ── Marker (photodiode) epoch tracking ───────────────────────────────────────
class MarkerTracker:
    """
    Tracks rising/falling edges of one bit of the digital-in word to define
    stimulus on/off epochs, in Intan sample-index units.
    """

    def __init__(self, bit_index):
        self.bit = bit_index
        self.prev_level = None
        self.epoch_start_ts = None
        self.epoch_count = 0

    def process(self, timestamps, digital):
        events = []
        levels = (digital >> self.bit) & 1
        for i in range(len(levels)):
            level = int(levels[i])
            ts = int(timestamps[i])
            if self.prev_level is None:
                self.prev_level = level
                continue
            if level == 1 and self.prev_level == 0:      # rising: stim ON
                self.epoch_start_ts = ts
                self.epoch_count += 1
                events.append({"type": "on", "ts": ts, "n": self.epoch_count})
            elif level == 0 and self.prev_level == 1:    # falling: stim OFF
                events.append({
                    "type": "off", "ts": ts,
                    "start": self.epoch_start_ts, "n": self.epoch_count,
                })
            self.prev_level = level
        return events


# ── Background acquisition worker ────────────────────────────────────────────
class ProbeWorker(threading.Thread):
    """
    Runs the connect/configure/stream loop off the GUI thread. Communicates with
    the GUI ONLY through a thread-safe queue (Tkinter is not thread-safe).

    Messages pushed to out_queue are (kind, payload) tuples:
        ("status", str)          general status text
        ("log", str)             a line for the event log
        ("rates", {ch: rate})    latest per-channel spike rate (sp/s)
        ("marker", ("on"/"off", epoch_no))
        ("epoch", dict)          closed-epoch summary with per-channel counts
        ("error", str)           fatal error; worker stops after this
        ("stopped", None)        worker has fully stopped
    """

    def __init__(self, cfg, out_queue):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.out = out_queue
        self._stop = threading.Event()
        self._dump_request = threading.Event()

    def stop(self):
        self._stop.set()

    def request_dump(self):
        self._dump_request.set()

    def _emit(self, kind, payload=None):
        self.out.put((kind, payload))

    def run(self):
        cfg = self.cfg
        cmd = wave = None
        try:
            self._emit("status", f"Connecting command {cfg['host']}:{cfg['cmd_port']} ...")
            cmd = RHXCommandClient(cfg["host"], cfg["cmd_port"])
            sample_rate = cmd.get_sample_rate()
            ctrl = cmd.get("type")
            self._emit("log", f"Connected. Controller={ctrl!r}  {sample_rate:.0f} Hz")

            cmd.set_runmode("stop")
            time.sleep(0.1)
            cmd.execute("clearalldataoutputs")
            time.sleep(0.05)
            for ch in cfg["channels"]:
                cmd.set(f"{ch.lower()}.tcpdataoutputenabled", "true")
            has_digital = cfg["use_digital"]
            if has_digital:
                self._emit("log", f"Enabling digital-in: {cfg['digital_enable_cmd']!r}")
                cmd._send(cfg["digital_enable_cmd"])
            time.sleep(0.1)

            wave = WaveformStream(cfg["host"], cfg["wave_port"],
                                  len(cfg["channels"]), has_digital)
            self._emit("log",
                       f"Assuming bytes_per_frame={wave.bytes_per_frame} "
                       f"(4 ts + {len(cfg['channels'])}x2 amp"
                       f"{' + 2 digital' if has_digital else ''}), "
                       f"block={wave.bytes_per_block}")

            mode = "record" if cfg["record"] else "run"
            self._emit("status", f"Starting RHX (runmode {mode}) ...")
            wave.flush()
            cmd.set_runmode(mode)

            detected = wave.detect_block_size()
            if detected is None:
                self._emit("log", "WARNING: couldn't auto-detect block size yet "
                                  "(is data flowing?). Continuing.")
            elif detected != wave.bytes_per_block:
                per_frame = (detected - 4) / FRAMES_PER_BLOCK
                self._emit("log", "*** FRAME-SIZE MISMATCH ***")
                self._emit("log", f"  detected block={detected} "
                                  f"({per_frame:.3f} B/frame)")
                self._emit("log", f"  assumed  block={wave.bytes_per_block} "
                                  f"({wave.bytes_per_frame} B/frame)")
                self._emit("log", "  Digital-word placement/size or extra bands "
                                  "differ. Use 'Dump one frame' and adjust the "
                                  "parser. Stopping to avoid garbage.")
                self._emit("error", "Frame-size mismatch (see log).")
                return
            else:
                self._emit("log", f"Frame size confirmed from stream: "
                                  f"{detected} B/block. OK.")

            self._stream_loop(cmd, wave, sample_rate, has_digital)

        except Exception as e:
            self._emit("error", str(e))
        finally:
            try:
                if cmd is not None:
                    cmd.set_runmode("stop")
            except Exception:
                pass
            if wave is not None:
                wave.close()
            if cmd is not None:
                cmd.close()
            self._emit("stopped", None)

    def _stream_loop(self, cmd, wave, sample_rate, has_digital):
        cfg = self.cfg
        channels = cfg["channels"]
        window_samples = int(cfg["window_ms"] / 1000.0 * sample_rate)
        hist_len = int(cfg["hist_sec"] * sample_rate)
        ring = [deque(maxlen=window_samples) for _ in channels]
        hist_ts = deque(maxlen=hist_len)
        hist_amp = [deque(maxlen=hist_len) for _ in channels]
        marker = MarkerTracker(cfg["marker_bit"]) if has_digital else None
        last_report = time.time()

        self._emit("status", "Streaming — flash the stimulus to make epochs.")
        while not self._stop.is_set():
            out = wave.read_frames()
            if out is None:
                time.sleep(0.01)
                continue
            timestamps, amp, digital = out

            for ci in range(len(channels)):
                ring[ci].extend(amp[ci])
                hist_amp[ci].extend(amp[ci])
            hist_ts.extend(timestamps.tolist())

            if self._dump_request.is_set():
                self._dump_request.clear()
                self._emit("log", f"DUMP  ts0={int(timestamps[0])}  "
                                  f"amp[:,0]uV={np.round(amp[:, 0], 1).tolist()}"
                                  + (f"  dig0=0b{int(digital[0]):016b}"
                                     if digital is not None else ""))

            if marker is not None and digital is not None:
                for ev in marker.process(timestamps, digital):
                    if ev["type"] == "on":
                        self._emit("marker", ("on", ev["n"]))
                        self._emit("log", f"MARKER ON   #{ev['n']}  "
                                          f"t={ev['ts']/sample_rate:.4f}s")
                    else:
                        self._emit("marker", ("off", ev["n"]))
                        self._report_epoch(ev, sample_rate, hist_ts, hist_amp)

            now = time.time()
            if now - last_report >= cfg["report_sec"]:
                last_report = now
                rates = {}
                for ci, ch in enumerate(channels):
                    buf = np.fromiter(ring[ci], dtype=np.float64)
                    if len(buf) < max(8, window_samples // 4):
                        rates[ch] = None
                        continue
                    n = len(detect_spikes(buf, sample_rate,
                                          threshold_rms=cfg["threshold_rms"]))
                    dur = len(buf) / sample_rate
                    rates[ch] = n / dur if dur > 0 else 0.0
                self._emit("rates", rates)

    def _report_epoch(self, ev, sample_rate, hist_ts, hist_amp):
        cfg = self.cfg
        start, end = ev["start"], ev["ts"]
        if start is None:
            self._emit("log", f"MARKER OFF  #{ev['n']}  (no matching ON edge)")
            return
        dur_ms = (end - start) / sample_rate * 1000.0
        lo = start + int(cfg["left_ms"] / 1000.0 * sample_rate)
        hi = end + int(cfg["right_ms"] / 1000.0 * sample_rate)
        ts_arr = np.fromiter(hist_ts, dtype=np.int64)
        counts = {}
        if ts_arr.size and (ts_arr >= lo).any() and (ts_arr <= hi).any():
            mask = (ts_arr >= lo) & (ts_arr <= hi)
            win_dur = max((hi - lo) / sample_rate, 1e-9)
            for ci, ch in enumerate(cfg["channels"]):
                seg = np.fromiter(hist_amp[ci], dtype=np.float64)[mask]
                if len(seg) < 8:
                    counts[ch] = None
                    continue
                n = len(detect_spikes(seg, sample_rate,
                                      threshold_rms=cfg["threshold_rms"]))
                counts[ch] = (n, n / win_dur)
            parts = ", ".join(
                f"{ch}: {v[0]} sp ({v[1]:.1f}/s)" if v else f"{ch}: n/a"
                for ch, v in counts.items())
        else:
            parts = "(epoch not in history — increase history seconds)"
        self._emit("epoch", {"n": ev["n"], "dur_ms": dur_ms, "text": parts})
        self._emit("log", f"MARKER OFF  #{ev['n']}  dur={dur_ms:.1f}ms  -> {parts}")


# ── GUI ──────────────────────────────────────────────────────────────────────
def launch_gui():
    import tkinter as tk
    from tkinter import ttk

    RATE_HISTORY = 120  # points kept in the rolling plot per channel

    root = tk.Tk()
    root.title("RF Plotter — Live Spike + Marker Probe (Phase 0)")
    root.geometry("900x640")

    out_queue: "queue.Queue" = queue.Queue()
    state = {"worker": None, "rate_hist": {}, "channels": [], "marker_on": False}

    # ---- Settings form ----
    form = ttk.LabelFrame(root, text="Connection & settings")
    form.pack(fill="x", padx=8, pady=6)

    def add_field(row, col, label, default, width=12):
        ttk.Label(form, text=label).grid(row=row, column=col*2, sticky="e",
                                         padx=4, pady=3)
        var = tk.StringVar(value=str(default))
        ttk.Entry(form, textvariable=var, width=width).grid(
            row=row, column=col*2 + 1, sticky="w", padx=4, pady=3)
        return var

    host_v = add_field(0, 0, "Host", "127.0.0.1")
    cmd_v = add_field(0, 1, "Command port", "5000", 8)
    wave_v = add_field(0, 2, "Waveform port", "5001", 8)
    chan_v = add_field(1, 0, "Channels (comma)", "A-000", 20)
    bit_v = add_field(1, 1, "Marker bit", "1", 6)
    thr_v = add_field(1, 2, "Threshold x RMS", "4.0", 6)
    win_v = add_field(2, 0, "Rate window (ms)", "1000", 8)
    left_v = add_field(2, 1, "Latency left (ms)", "0", 6)
    right_v = add_field(2, 2, "Latency right (ms)", "0", 6)
    digcmd_v = add_field(3, 0, "Digital enable cmd",
                         "set digitalin.tcpdataoutputenabled true", 40)

    use_dig_v = tk.BooleanVar(value=True)
    ttk.Checkbutton(form, text="Use digital marker", variable=use_dig_v).grid(
        row=3, column=4, sticky="w", padx=4)
    rec_v = tk.BooleanVar(value=False)
    ttk.Checkbutton(form, text="Record to disk", variable=rec_v).grid(
        row=3, column=5, sticky="w", padx=4)

    # ---- Controls ----
    controls = ttk.Frame(root)
    controls.pack(fill="x", padx=8)
    start_btn = ttk.Button(controls, text="Start")
    stop_btn = ttk.Button(controls, text="Stop", state="disabled")
    dump_btn = ttk.Button(controls, text="Dump one frame", state="disabled")
    start_btn.pack(side="left", padx=4, pady=4)
    stop_btn.pack(side="left", padx=4)
    dump_btn.pack(side="left", padx=4)
    marker_lbl = tk.Label(controls, text="MARKER: —", width=16,
                          relief="ridge", bg="#ddd")
    marker_lbl.pack(side="right", padx=6)
    status_var = tk.StringVar(value="Idle. Set fields and click Start.")
    ttk.Label(controls, textvariable=status_var).pack(side="right", padx=8)

    # ---- Live rate labels ----
    rates_frame = ttk.LabelFrame(root, text="Live spike rate (sp/s)")
    rates_frame.pack(fill="x", padx=8, pady=6)
    rate_labels = {}

    # ---- Rolling plot ----
    plot = tk.Canvas(root, height=220, bg="white")
    plot.pack(fill="both", expand=False, padx=8, pady=4)
    COLORS = ["#e6194B", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
              "#42d4f4", "#f032e6", "#bfef45"]

    # ---- Event log ----
    log_frame = ttk.LabelFrame(root, text="Event log")
    log_frame.pack(fill="both", expand=True, padx=8, pady=6)
    log = tk.Text(log_frame, height=10, wrap="none")
    log.pack(side="left", fill="both", expand=True)
    log_sb = ttk.Scrollbar(log_frame, command=log.yview)
    log_sb.pack(side="right", fill="y")
    log.config(yscrollcommand=log_sb.set)

    def log_line(text):
        log.insert("end", time.strftime("%H:%M:%S ") + text + "\n")
        log.see("end")

    def parse_channels():
        return [c.strip() for c in chan_v.get().replace(",", " ").split() if c.strip()]

    def build_rate_ui(channels):
        for w in rates_frame.winfo_children():
            w.destroy()
        rate_labels.clear()
        state["rate_hist"] = {ch: deque(maxlen=RATE_HISTORY) for ch in channels}
        for i, ch in enumerate(channels):
            ttk.Label(rates_frame, text=ch + ":",
                      foreground=COLORS[i % len(COLORS)]).grid(
                row=0, column=i * 2, sticky="e", padx=(10, 2))
            v = tk.StringVar(value="—")
            rate_labels[ch] = v
            ttk.Label(rates_frame, textvariable=v, width=8).grid(
                row=0, column=i * 2 + 1, sticky="w")

    def redraw_plot():
        plot.delete("all")
        w = plot.winfo_width() or 880
        h = plot.winfo_height() or 220
        hist = state["rate_hist"]
        all_vals = [v for dq in hist.values() for v in dq]
        vmax = max(all_vals) if all_vals else 1.0
        vmax = max(vmax, 1.0)
        # axes
        plot.create_line(40, h - 20, w - 5, h - 20, fill="#aaa")
        plot.create_line(40, 10, 40, h - 20, fill="#aaa")
        plot.create_text(38, 12, text=f"{vmax:.0f}", anchor="e", fill="#666")
        plot.create_text(38, h - 22, text="0", anchor="e", fill="#666")
        plot.create_text(44, 12, text="sp/s", anchor="w", fill="#666")
        for i, (ch, dq) in enumerate(hist.items()):
            if len(dq) < 2:
                continue
            color = COLORS[i % len(COLORS)]
            n = len(dq)
            pts = []
            for j, val in enumerate(dq):
                x = 40 + (w - 45) * (j / (RATE_HISTORY - 1))
                y = (h - 20) - (h - 30) * (val / vmax)
                pts.extend([x, y])
            plot.create_line(*pts, fill=color, width=2)

    def set_running(running):
        start_btn.config(state="disabled" if running else "normal")
        stop_btn.config(state="normal" if running else "disabled")
        dump_btn.config(state="normal" if running else "disabled")
        for child in form.winfo_children():
            if isinstance(child, ttk.Entry):
                child.config(state="disabled" if running else "normal")

    def on_start():
        channels = parse_channels()
        if not channels:
            log_line("No channels entered.")
            return
        try:
            cfg = {
                "host": host_v.get().strip(),
                "cmd_port": int(cmd_v.get()),
                "wave_port": int(wave_v.get()),
                "channels": channels,
                "marker_bit": int(bit_v.get()),
                "threshold_rms": float(thr_v.get()),
                "window_ms": float(win_v.get()),
                "left_ms": float(left_v.get()),
                "right_ms": float(right_v.get()),
                "digital_enable_cmd": digcmd_v.get().strip(),
                "use_digital": bool(use_dig_v.get()),
                "record": bool(rec_v.get()),
                "report_sec": 1.0,
                "hist_sec": 5.0,
            }
        except ValueError as e:
            log_line(f"Bad field value: {e}")
            return
        state["channels"] = channels
        build_rate_ui(channels)
        worker = ProbeWorker(cfg, out_queue)
        state["worker"] = worker
        set_running(True)
        log_line("Starting ...")
        worker.start()

    def on_stop():
        w = state["worker"]
        if w is not None:
            status_var.set("Stopping ...")
            w.stop()

    def on_dump():
        w = state["worker"]
        if w is not None:
            w.request_dump()

    start_btn.config(command=on_start)
    stop_btn.config(command=on_stop)
    dump_btn.config(command=on_dump)

    def set_marker(on):
        state["marker_on"] = on
        marker_lbl.config(text="MARKER: ON" if on else "MARKER: OFF",
                          bg="#7CFC7C" if on else "#ddd")

    def poll_queue():
        try:
            while True:
                kind, payload = out_queue.get_nowait()
                if kind == "status":
                    status_var.set(payload)
                elif kind == "log":
                    log_line(payload)
                elif kind == "rates":
                    for ch, r in payload.items():
                        if ch in rate_labels:
                            rate_labels[ch].set("buffering" if r is None
                                                else f"{r:6.1f}")
                        if r is not None and ch in state["rate_hist"]:
                            state["rate_hist"][ch].append(r)
                    redraw_plot()
                elif kind == "marker":
                    set_marker(payload[0] == "on")
                elif kind == "epoch":
                    pass  # already logged; hook for future per-epoch UI
                elif kind == "error":
                    log_line("ERROR: " + payload)
                    status_var.set("Error — see log.")
                elif kind == "stopped":
                    set_running(False)
                    set_marker(False)
                    status_var.set("Stopped.")
                    state["worker"] = None
        except queue.Empty:
            pass
        root.after(50, poll_queue)

    def on_close():
        w = state["worker"]
        if w is not None:
            w.stop()
            w.join(timeout=3.0)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.after(50, poll_queue)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
