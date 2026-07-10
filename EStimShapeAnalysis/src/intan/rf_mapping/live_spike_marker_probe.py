#!/usr/bin/env python3
"""
Phase 0 — Live Spike + Marker Probe (Intan RHX)
===============================================
A small GUI (Tkinter, no command line) that de-risks the RF-Plotter live-tuning
feature and DISCOVERS the exact RHX TCP stream layout on your rig. It:

  1. Streams amplifier data live from RHX and detects spikes (per channel).
  2. Auto-detects how many extra 2-byte "aux" fields the waveform stream carries
     per frame (these are your enabled digital-in / analog-in channels) and shows
     them live, so you can identify which one is the photodiode MARKER by flashing.
  3. Once you point it at the marker field, shows the spike count inside each
     marker epoch — the measurement Phase 1 will log per stimulus presentation.

Run it by opening this file in your IDE and clicking Run (no terminal, no
arguments). It is SELF-CONTAINED (own sockets, spike detection inlined) and does
NOT depend on the abandoned companion app. Only numpy/scipy are needed; the GUI
is stdlib Tkinter.

--------------------------------------------------------------------------------
RHX setup (in the Intan RHX software first)
--------------------------------------------------------------------------------
  Network -> Remote TCP Control:
    * Command Output   : <host> : 5000  -> Listen  (status "Pending")
    * Waveform Output  : <host> : 5001  -> Listen  (status "Pending")

The probe enables the amplifier channels you type in (WIDE band). To get the
marker it also sends whatever "extra channel enable" commands you put in the box
(one per line). The digital-in native names vary by RHX build — if no aux field
appears, check the channel's native name in RHX's Data Output tab and edit the
commands. Common forms to try: DIGITAL-IN-01, DIGITAL-IN-1, or an analog input
ANALOG-IN-1 if your photodiode is wired to an ADC.

--------------------------------------------------------------------------------
How discovery works
--------------------------------------------------------------------------------
The stream frames as: [magic][ 128 x frame ], frame = [int32 timestamp]
[uint16 per amp channel][uint16 per enabled aux channel]. The probe measures the
byte distance between magic numbers to learn the true frame size, computes how
many aux fields are present, parses them, and flags any aux field whose value
changes while streaming (flash the stimulus -> the marker field lights up).
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
BYTES_PER_SAMPLE = 2            # uint16 per amp channel and per aux field


# ── Command socket ───────────────────────────────────────────────────────────
class RHXCommandClient:
    """Text command socket to RHX (get/set/execute)."""

    def __init__(self, host, port, timeout=1.0):
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


# ── Waveform socket + adaptive block parsing ─────────────────────────────────
class WaveformStream:
    """
    Reads RHX waveform blocks. Each frame is:
        [int32 timestamp][uint16 * n_amp][uint16 * n_aux]
    n_aux (extra enabled digital-in / analog-in fields) is discovered from the
    stream, not assumed. Set it with set_n_aux() after detect_block_size().
    """

    def __init__(self, host, port, n_amp, timeout=5.0):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect((host, port))
        self.n_amp = n_amp
        self.n_aux = 0
        self._buf = bytearray()
        self._recompute()

    def _recompute(self):
        self.bytes_per_frame = (
            BYTES_TIMESTAMP + (self.n_amp + self.n_aux) * BYTES_PER_SAMPLE
        )
        self.bytes_per_block = 4 + FRAMES_PER_BLOCK * self.bytes_per_frame

    def set_n_aux(self, n_aux):
        self.n_aux = n_aux
        self._recompute()

    def flush(self):
        self._drain()
        self._buf = bytearray()

    def _drain(self):
        self.sock.setblocking(False)
        try:
            while True:
                chunk = self.sock.recv(65536)
                if not chunk:
                    break
                self._buf.extend(chunk)
        except (BlockingIOError, socket.error):
            pass
        finally:
            self.sock.setblocking(True)

    def _recv_available(self):
        self._drain()

    def detect_block_size(self, settle_sec=0.5):
        """Byte distance between two consecutive magic numbers, or None."""
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

    def align_to_magic(self):
        """Drop any bytes before the first magic so reads are block-aligned."""
        data = bytes(self._buf)
        first = data.find(struct.pack("<I", MAGIC_NUMBER))
        if first > 0:
            del self._buf[:first]
        return first

    def read_frames(self):
        """
        Return (timestamps, amp_uV, aux) for all currently-available complete
        blocks, or None if none ready.
            timestamps : int32 (n_frames,)
            amp_uV     : float64 (n_amp, n_frames)
            aux        : uint16 (n_aux, n_frames) or None
        Vectorized parse (fast enough for 30 kHz x several channels).
        """
        self._recv_available()
        if len(self._buf) < self.bytes_per_block:
            return None

        n_blocks = len(self._buf) // self.bytes_per_block
        usable = n_blocks * self.bytes_per_block
        raw = np.frombuffer(bytes(self._buf[:usable]), dtype=np.uint8)
        del self._buf[:usable]

        blocks = raw.reshape(n_blocks, self.bytes_per_block)
        magics = blocks[:, 0:4].copy().view("<u4").ravel()
        if not np.all(magics == MAGIC_NUMBER):
            raise ValueError(
                f"Frame desync: a block did not start with magic "
                f"0x{MAGIC_NUMBER:08x} (bytes_per_frame={self.bytes_per_frame})."
            )

        frames = blocks[:, 4:].reshape(n_blocks * FRAMES_PER_BLOCK,
                                       self.bytes_per_frame)
        ts = frames[:, 0:4].copy().view("<i4").ravel()

        amp_end = 4 + self.n_amp * 2
        amp_u16 = frames[:, 4:amp_end].copy().view("<u2")  # (frames, n_amp)
        amp = (MICROVOLTS_PER_BIT * (amp_u16.astype(np.float64) - SAMPLE_OFFSET)).T

        aux = None
        if self.n_aux > 0:
            aux_u16 = frames[:, amp_end:amp_end + self.n_aux * 2].copy().view("<u2")
            aux = aux_u16.T.copy()  # (n_aux, frames)

        return ts, amp, aux

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


# ── Spike detection (inlined; mirrors lfp/mua_detection.py) ───────────────────
def detect_spikes(wideband, sample_rate, highpass_hz=300.0,
                  threshold_rms=4.0, refractory_sec=0.001):
    """-N x RMS threshold MUA detection. Returns sample indices of spikes."""
    if _HAVE_SCIPY:
        nyq = sample_rate / 2.0
        sos = butter(4, highpass_hz / nyq, btype="high", output="sos")
        filtered = sosfilt(sos, wideband)
    else:
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


# ── Marker epoch tracking (generic on a 0/1 level array) ─────────────────────
class MarkerTracker:
    """Tracks rising/falling edges of a per-frame 0/1 level to define epochs."""

    def __init__(self):
        self.prev_level = None
        self.epoch_start_ts = None
        self.epoch_count = 0

    def process(self, timestamps, levels):
        events = []
        for i in range(len(levels)):
            level = int(levels[i])
            ts = int(timestamps[i])
            if self.prev_level is None:
                self.prev_level = level
                continue
            if level == 1 and self.prev_level == 0:
                self.epoch_start_ts = ts
                self.epoch_count += 1
                events.append({"type": "on", "ts": ts, "n": self.epoch_count})
            elif level == 0 and self.prev_level == 1:
                events.append({"type": "off", "ts": ts,
                               "start": self.epoch_start_ts, "n": self.epoch_count})
            self.prev_level = level
        return events


# ── Background acquisition worker ────────────────────────────────────────────
class ProbeWorker(threading.Thread):
    """
    Connect/configure/stream off the GUI thread. Talks to the GUI only through a
    thread-safe queue. Messages: ("status"|"log"|"rates"|"aux"|"marker"|"epoch"
    |"error"|"stopped", payload).
    """

    def __init__(self, cfg, out_queue):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.out = out_queue
        self._stop = threading.Event()
        self._dump = threading.Event()

    def stop(self):
        self._stop.set()

    def request_dump(self):
        self._dump.set()

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
            cmd.execute("clearalldataoutputs")
            for ch in cfg["channels"]:
                cmd.set(f"{ch.lower()}.tcpdataoutputenabled", "true")
            for line in cfg["aux_enable_cmds"]:
                if line.strip():
                    self._emit("log", f"aux enable -> {line.strip()!r}")
                    cmd._send(line.strip())

            wave = WaveformStream(cfg["host"], cfg["wave_port"], len(cfg["channels"]))
            mode = "record" if cfg["record"] else "run"
            self._emit("status", f"Starting RHX (runmode {mode}) ...")
            wave.flush()
            cmd.set_runmode(mode)

            n_aux = self._negotiate_layout(wave, len(cfg["channels"]))
            if n_aux is None:
                self._emit("error", "Could not determine frame layout (no data?).")
                return

            self._stream_loop(wave, sample_rate, n_aux)

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

    def _negotiate_layout(self, wave, n_amp):
        """Detect true frame size from the stream and set n_aux accordingly."""
        block = wave.detect_block_size()
        if block is None:
            return None
        payload = block - 4
        if payload <= 0 or payload % FRAMES_PER_BLOCK != 0:
            self._emit("log", f"Odd block size {block}; cannot interpret.")
            return None
        bpf = payload // FRAMES_PER_BLOCK
        extra = bpf - BYTES_TIMESTAMP - n_amp * BYTES_PER_SAMPLE
        if extra < 0 or extra % BYTES_PER_SAMPLE != 0:
            self._emit("log", f"Frame {bpf} B doesn't fit {n_amp} amp channels. "
                              f"Check that exactly these channels are enabled.")
            return None
        n_aux = extra // BYTES_PER_SAMPLE
        wave.set_n_aux(n_aux)
        wave.align_to_magic()
        self._emit("log", f"Frame confirmed: {bpf} B/frame = 4 ts + {n_amp}x2 amp "
                          f"+ {n_aux}x2 aux. block={block} B.")
        if n_aux == 0 and self.cfg["use_marker"]:
            self._emit("log", "No aux fields present — your marker-enable "
                              "command(s) added nothing. Edit the 'extra channel "
                              "enable' box (verify the digital-in native name in "
                              "RHX's Data Output tab). Streaming spikes only.")
        elif n_aux > 0:
            self._emit("log", f"{n_aux} aux field(s) detected. Flash the stimulus "
                              f"— the marker field's value will change. Set "
                              f"'marker aux index' to it.")
        return n_aux

    def _stream_loop(self, wave, sample_rate, n_aux):
        cfg = self.cfg
        channels = cfg["channels"]
        window_samples = int(cfg["window_ms"] / 1000.0 * sample_rate)
        hist_len = int(cfg["hist_sec"] * sample_rate)
        ring = [deque(maxlen=window_samples) for _ in channels]
        hist_ts = deque(maxlen=hist_len)
        hist_amp = [deque(maxlen=hist_len) for _ in channels]

        marker_idx = cfg["marker_aux_index"]
        marker_bit = cfg["marker_bit"]
        marker_on = cfg["use_marker"] and n_aux > 0 and marker_idx < n_aux
        tracker = MarkerTracker() if marker_on else None
        aux_min = np.full(n_aux, np.iinfo(np.uint16).max, dtype=np.int64) if n_aux else None
        aux_max = np.zeros(n_aux, dtype=np.int64) if n_aux else None

        last_report = time.time()
        self._emit("status", "Streaming.")
        while not self._stop.is_set():
            out = wave.read_frames()
            if out is None:
                time.sleep(0.01)
                continue
            ts, amp, aux = out

            for ci in range(len(channels)):
                ring[ci].extend(amp[ci])
                hist_amp[ci].extend(amp[ci])
            hist_ts.extend(ts.tolist())

            if aux is not None and n_aux:
                aux_min = np.minimum(aux_min, aux.min(axis=1))
                aux_max = np.maximum(aux_max, aux.max(axis=1))

            if self._dump.is_set():
                self._dump.clear()
                aux0 = (f"  aux[:,0]={aux[:, 0].tolist()}" if aux is not None else "")
                self._emit("log", f"DUMP ts0={int(ts[0])} "
                                  f"amp[:,0]uV={np.round(amp[:, 0], 1).tolist()}{aux0}")

            if tracker is not None and aux is not None:
                row = aux[marker_idx].astype(np.int64)
                levels = ((row >> marker_bit) & 1) if marker_bit >= 0 else (row != 0).astype(np.int64)
                for ev in tracker.process(ts, levels):
                    if ev["type"] == "on":
                        self._emit("marker", ("on", ev["n"]))
                        self._emit("log", f"MARKER ON  #{ev['n']} t={ev['ts']/sample_rate:.4f}s")
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
                    n = len(detect_spikes(buf, sample_rate, threshold_rms=cfg["threshold_rms"]))
                    dur = len(buf) / sample_rate
                    rates[ch] = n / dur if dur > 0 else 0.0
                self._emit("rates", rates)
                if n_aux and aux is not None:
                    self._emit("aux", {
                        "cur": aux[:, -1].tolist(),
                        "changed": [int(aux_max[i] > aux_min[i]) for i in range(n_aux)],
                        "marker_idx": marker_idx if marker_on else -1,
                    })

    def _report_epoch(self, ev, sample_rate, hist_ts, hist_amp):
        cfg = self.cfg
        start, end = ev["start"], ev["ts"]
        if start is None:
            self._emit("log", f"MARKER OFF #{ev['n']} (no matching ON)")
            return
        dur_ms = (end - start) / sample_rate * 1000.0
        lo = start + int(cfg["left_ms"] / 1000.0 * sample_rate)
        hi = end + int(cfg["right_ms"] / 1000.0 * sample_rate)
        ts_arr = np.fromiter(hist_ts, dtype=np.int64)
        if ts_arr.size and (ts_arr >= lo).any() and (ts_arr <= hi).any():
            mask = (ts_arr >= lo) & (ts_arr <= hi)
            win_dur = max((hi - lo) / sample_rate, 1e-9)
            parts = []
            for ci, ch in enumerate(cfg["channels"]):
                seg = np.fromiter(hist_amp[ci], dtype=np.float64)[mask]
                if len(seg) < 8:
                    parts.append(f"{ch}: n/a")
                    continue
                n = len(detect_spikes(seg, sample_rate, threshold_rms=cfg["threshold_rms"]))
                parts.append(f"{ch}: {n} sp ({n/win_dur:.1f}/s)")
            text = ", ".join(parts)
        else:
            text = "(epoch not in history — increase history seconds)"
        self._emit("epoch", {"n": ev["n"], "dur_ms": dur_ms, "text": text})
        self._emit("log", f"MARKER OFF #{ev['n']} dur={dur_ms:.1f}ms -> {text}")


# ── GUI ──────────────────────────────────────────────────────────────────────
def launch_gui():
    import tkinter as tk
    from tkinter import ttk

    RATE_HISTORY = 120

    root = tk.Tk()
    root.title("RF Plotter — Live Spike + Marker Probe (Phase 0)")
    root.geometry("940x760")

    out_queue: "queue.Queue" = queue.Queue()
    state = {"worker": None, "rate_hist": {}, "channels": []}

    form = ttk.LabelFrame(root, text="Connection & settings")
    form.pack(fill="x", padx=8, pady=6)

    def field(row, col, label, default, width=12):
        ttk.Label(form, text=label).grid(row=row, column=col*2, sticky="e", padx=4, pady=3)
        var = tk.StringVar(value=str(default))
        ttk.Entry(form, textvariable=var, width=width).grid(
            row=row, column=col*2 + 1, sticky="w", padx=4, pady=3)
        return var

    host_v = field(0, 0, "Host", "127.0.0.1")
    cmd_v = field(0, 1, "Command port", "5000", 8)
    wave_v = field(0, 2, "Waveform port", "5001", 8)
    chan_v = field(1, 0, "Channels (comma)", "A-000", 20)
    thr_v = field(1, 1, "Threshold x RMS", "4.0", 6)
    win_v = field(1, 2, "Rate window (ms)", "1000", 8)
    midx_v = field(2, 0, "Marker aux index", "0", 6)
    mbit_v = field(2, 1, "Marker bit (-1=nonzero)", "-1", 6)
    left_v = field(2, 2, "Latency left (ms)", "0", 6)
    right_v = field(3, 0, "Latency right (ms)", "0", 6)

    use_marker_v = tk.BooleanVar(value=True)
    ttk.Checkbutton(form, text="Track marker", variable=use_marker_v).grid(
        row=3, column=2, sticky="w", padx=4)
    rec_v = tk.BooleanVar(value=False)
    ttk.Checkbutton(form, text="Record to disk", variable=rec_v).grid(
        row=3, column=3, sticky="w", padx=4)

    ttk.Label(form, text="Extra channel enable (one per line):").grid(
        row=4, column=0, columnspan=2, sticky="w", padx=4, pady=(6, 0))
    aux_text = tk.Text(form, height=3, width=70)
    aux_text.grid(row=5, column=0, columnspan=6, sticky="we", padx=4, pady=2)
    aux_text.insert("1.0",
                    "set DIGITAL-IN-02.tcpdataoutputenabled true\n"
                    "# If no aux field appears, verify the native name in RHX's\n"
                    "# Data Output tab (e.g. DIGITAL-IN-1, or ANALOG-IN-1 for a "
                    "photodiode on an ADC).")

    controls = ttk.Frame(root)
    controls.pack(fill="x", padx=8)
    start_btn = ttk.Button(controls, text="Start")
    stop_btn = ttk.Button(controls, text="Stop", state="disabled")
    dump_btn = ttk.Button(controls, text="Dump one frame", state="disabled")
    start_btn.pack(side="left", padx=4, pady=4)
    stop_btn.pack(side="left", padx=4)
    dump_btn.pack(side="left", padx=4)
    marker_lbl = tk.Label(controls, text="MARKER: —", width=14, relief="ridge", bg="#ddd")
    marker_lbl.pack(side="right", padx=6)
    status_var = tk.StringVar(value="Idle. Set fields and click Start.")
    ttk.Label(controls, textvariable=status_var).pack(side="right", padx=8)

    rates_frame = ttk.LabelFrame(root, text="Live spike rate (sp/s)")
    rates_frame.pack(fill="x", padx=8, pady=4)
    rate_labels = {}

    aux_frame = ttk.LabelFrame(root, text="Aux fields (enabled digital/analog) — "
                                         "flash the stimulus; the one that CHANGES is the marker")
    aux_frame.pack(fill="x", padx=8, pady=4)
    aux_var = tk.StringVar(value="(none yet)")
    ttk.Label(aux_frame, textvariable=aux_var, font=("TkFixedFont", 10)).pack(
        anchor="w", padx=6, pady=4)

    plot = tk.Canvas(root, height=200, bg="white")
    plot.pack(fill="both", expand=False, padx=8, pady=4)
    COLORS = ["#e6194B", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
              "#42d4f4", "#f032e6", "#bfef45"]

    log_frame = ttk.LabelFrame(root, text="Event log")
    log_frame.pack(fill="both", expand=True, padx=8, pady=6)
    log = tk.Text(log_frame, height=9, wrap="none")
    log.pack(side="left", fill="both", expand=True)
    sb = ttk.Scrollbar(log_frame, command=log.yview)
    sb.pack(side="right", fill="y")
    log.config(yscrollcommand=sb.set)

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
                row=0, column=i*2, sticky="e", padx=(10, 2))
            v = tk.StringVar(value="—")
            rate_labels[ch] = v
            ttk.Label(rates_frame, textvariable=v, width=8).grid(
                row=0, column=i*2 + 1, sticky="w")

    def redraw_plot():
        plot.delete("all")
        w = plot.winfo_width() or 900
        h = plot.winfo_height() or 200
        hist = state["rate_hist"]
        all_vals = [v for dq in hist.values() for v in dq]
        vmax = max(max(all_vals) if all_vals else 1.0, 1.0)
        plot.create_line(40, h-20, w-5, h-20, fill="#aaa")
        plot.create_line(40, 10, 40, h-20, fill="#aaa")
        plot.create_text(38, 12, text=f"{vmax:.0f}", anchor="e", fill="#666")
        plot.create_text(38, h-22, text="0", anchor="e", fill="#666")
        for i, (ch, dq) in enumerate(hist.items()):
            if len(dq) < 2:
                continue
            pts = []
            for j, val in enumerate(dq):
                x = 40 + (w-45) * (j / (RATE_HISTORY-1))
                y = (h-20) - (h-30) * (val / vmax)
                pts.extend([x, y])
            plot.create_line(*pts, fill=COLORS[i % len(COLORS)], width=2)

    def set_running(running):
        start_btn.config(state="disabled" if running else "normal")
        stop_btn.config(state="normal" if running else "disabled")
        dump_btn.config(state="normal" if running else "disabled")

    def set_marker(on):
        marker_lbl.config(text="MARKER: ON" if on else "MARKER: OFF",
                          bg="#7CFC7C" if on else "#ddd")

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
                "threshold_rms": float(thr_v.get()),
                "window_ms": float(win_v.get()),
                "marker_aux_index": int(midx_v.get()),
                "marker_bit": int(mbit_v.get()),
                "left_ms": float(left_v.get()),
                "right_ms": float(right_v.get()),
                "use_marker": bool(use_marker_v.get()),
                "record": bool(rec_v.get()),
                "aux_enable_cmds": [ln for ln in aux_text.get("1.0", "end").splitlines()
                                    if ln.strip() and not ln.strip().startswith("#")],
                "report_sec": 1.0,
                "hist_sec": 5.0,
            }
        except ValueError as e:
            log_line(f"Bad field value: {e}")
            return
        state["channels"] = channels
        build_rate_ui(channels)
        aux_var.set("(waiting for stream ...)")
        worker = ProbeWorker(cfg, out_queue)
        state["worker"] = worker
        set_running(True)
        log_line("Starting ...")
        worker.start()

    def on_stop():
        if state["worker"] is not None:
            status_var.set("Stopping ...")
            state["worker"].stop()

    def on_dump():
        if state["worker"] is not None:
            state["worker"].request_dump()

    start_btn.config(command=on_start)
    stop_btn.config(command=on_stop)
    dump_btn.config(command=on_dump)

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
                            rate_labels[ch].set("buffering" if r is None else f"{r:6.1f}")
                        if r is not None and ch in state["rate_hist"]:
                            state["rate_hist"][ch].append(r)
                    redraw_plot()
                elif kind == "aux":
                    cur, changed, midx = payload["cur"], payload["changed"], payload["marker_idx"]
                    parts = []
                    for i, val in enumerate(cur):
                        tag = ""
                        if i == midx:
                            tag = " <-marker"
                        elif changed[i]:
                            tag = " *changing*"
                        parts.append(f"[{i}]={val} (0x{val:04x}){tag}")
                    aux_var.set("   ".join(parts))
                elif kind == "marker":
                    set_marker(payload[0] == "on")
                elif kind == "epoch":
                    pass
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
        if state["worker"] is not None:
            state["worker"].stop()
            state["worker"].join(timeout=3.0)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.after(50, poll_queue)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
