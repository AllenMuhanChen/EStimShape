#!/usr/bin/env python3
"""
Phase 0 — Live Spike + Marker Probe (Intan RHX, standalone)
===========================================================
De-risking tool for the RF-Plotter live-tuning feature. It proves, against your
actual rig, that we can:

  1. Stream amplifier data live from RHX over TCP and detect spikes (per channel).
  2. Read the photodiode MARKER (a digital-in bit) on the SAME stream, so spikes
     and stim on/off share Intan's sample clock and align exactly.
  3. Show the spike count that falls inside each marker epoch — the exact
     measurement Phase 1 will log per stimulus presentation.

This script is deliberately SELF-CONTAINED: it opens its own command/waveform
sockets and inlines spike detection. It does NOT import the (abandoned) companion
app. The only third-party deps are numpy and scipy.

--------------------------------------------------------------------------------
RHX setup (do this in the Intan RHX software first)
--------------------------------------------------------------------------------
  Network -> Remote TCP Control:
    * Command Output   : 127.0.0.1 : 5000  -> Listen  (status "Pending")
    * Waveform Output  : 127.0.0.1 : 5001  -> Listen  (status "Pending")
  (The Spike port is NOT used by this probe.)

You do NOT need to pre-enable channels; the probe enables exactly the channels
you pass on the command line (WIDE band) plus the digital inputs.

--------------------------------------------------------------------------------
Usage
--------------------------------------------------------------------------------
  python live_spike_marker_probe.py --channels A-000 --marker-bit 1
  python live_spike_marker_probe.py --host 172.30.6.78 --channels A-000 A-001 \
         --marker-bit 1 --threshold-rms 4.0 --window-ms 1000

Then flash your stimulus (F key in the mapper, or wave something past the
photodiode). You should see MARKER ON/OFF lines with epoch durations and the
spike count inside each epoch.

--------------------------------------------------------------------------------
THINGS TO CONFIRM ON THE RIG (why this is Phase 0)
--------------------------------------------------------------------------------
  * Digital-in enable command: this probe uses
        execute clearalldataoutputs
        set <ch>.tcpdataoutputenabled true          (WIDE band, per channel)
        set digitalin.tcpdataoutputenabled true     (<-- VERIFY this token)
    If your RHX build names it differently (e.g. per-line
    'digital-in-2.tcpdataoutputenabled'), pass --digital-enable-cmd to override,
    or --no-digital to run spikes-only first.
  * Frame layout: the probe AUTO-DETECTS the block size from the stream (distance
    between magic numbers) and checks it against the expected frame size. If the
    digital word is placed differently than assumed, you'll get a loud, explicit
    mismatch message instead of silent corruption. Use --dump-frame to print the
    raw layout for reverse-engineering against IntanRHX_TCPDocumentation.pdf.
  * Marker bit: "marker channel 2" is assumed to be DIGITAL-IN-2 == bit index 1
    (0-based). Override with --marker-bit if it's wired elsewhere.
"""

import argparse
import socket
import struct
import sys
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
        # "Return: ParamName Value..." -> value portion
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

    def _recv_available(self, first_timeout=1.0):
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
                    f"(bytes_per_frame={self.bytes_per_frame}). Re-run with "
                    f"--dump-frame to inspect, or --no-digital to isolate."
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
        """
        Feed a chunk of (timestamps, digital_word). Yields events as dicts:
          {"type": "on", "ts": <sample>}                     on rising edge
          {"type": "off", "ts": <sample>, "start": <sample>, "n": <epoch#>}
        """
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


# ── Main probe loop ──────────────────────────────────────────────────────────
def run(args):
    print(f"Connecting command socket {args.host}:{args.cmd_port} ...")
    cmd = RHXCommandClient(args.host, args.cmd_port)

    sample_rate = cmd.get_sample_rate()
    ctrl = cmd.get("type")
    print(f"Connected. Controller={ctrl!r}  sample_rate={sample_rate:.0f} Hz")

    # Make sure we're stopped before reconfiguring outputs.
    cmd.set_runmode("stop")
    time.sleep(0.1)

    # Configure TCP data outputs: WIDE band per requested channel + digital in.
    cmd.execute("clearalldataoutputs")
    time.sleep(0.05)
    for ch in args.channels:
        cmd.set(f"{ch.lower()}.tcpdataoutputenabled", "true")
    has_digital = not args.no_digital
    if has_digital:
        print(f"Enabling digital-in via: {args.digital_enable_cmd!r}")
        cmd._send(args.digital_enable_cmd)
    time.sleep(0.1)

    print(f"Connecting waveform socket {args.host}:{args.wave_port} ...")
    wave = WaveformStream(args.host, args.wave_port, len(args.channels), has_digital)
    print(f"Assuming bytes_per_frame={wave.bytes_per_frame} "
          f"(4 ts + {len(args.channels)}*2 amp"
          f"{' + 2 digital' if has_digital else ''}), "
          f"bytes_per_block={wave.bytes_per_block}")

    # Start the controller (run = stream only; record = stream + save to disk).
    mode = "record" if args.record else "run"
    print(f"Starting RHX (runmode {mode}) ...")
    wave.flush()
    cmd.set_runmode(mode)

    # Empirically confirm the frame layout.
    detected = wave.detect_block_size()
    if detected is None:
        print("WARNING: could not find two magic numbers to auto-detect block "
              "size yet (is data flowing? is a signal present?). Continuing.")
    elif detected != wave.bytes_per_block:
        exp_payload = detected - 4
        per_frame = exp_payload / FRAMES_PER_BLOCK
        print("\n*** FRAME-SIZE MISMATCH ***")
        print(f"  detected bytes_per_block = {detected} "
              f"(=> {per_frame:.3f} bytes/frame)")
        print(f"  assumed  bytes_per_block = {wave.bytes_per_block} "
              f"(=> {wave.bytes_per_frame} bytes/frame)")
        print("  The stream carries a different amount of data than assumed.")
        print("  Likely causes: digital word placement/size differs, or extra")
        print("  bands/channels are enabled. Inspect with --dump-frame and")
        print("  cross-check IntanRHX_TCPDocumentation.pdf, then adjust the")
        print("  parser. Aborting so we don't report garbage.\n")
        cmd.set_runmode("stop")
        wave.close(); cmd.close()
        return
    else:
        print(f"Frame size confirmed from stream: {detected} bytes/block. OK.\n")

    if args.dump_frame:
        _dump_first_frame(wave)

    marker = MarkerTracker(args.marker_bit) if has_digital else None

    # Rolling per-channel buffers for spike-rate over the last window.
    window_samples = int(args.window_ms / 1000.0 * sample_rate)
    ring = [deque(maxlen=window_samples) for _ in args.channels]
    # Buffer of (sample_index -> per-channel value) for epoch spike counting.
    # Keep a modest history so we can count spikes inside a just-closed epoch.
    hist_ts = deque(maxlen=int(args.hist_sec * sample_rate))
    hist_amp = [deque(maxlen=int(args.hist_sec * sample_rate)) for _ in args.channels]

    print("Streaming. Flash the stimulus to generate marker epochs. Ctrl-C to stop.\n")
    last_report = time.time()
    try:
        while True:
            out = wave.read_frames()
            if out is None:
                time.sleep(0.01)
                continue
            timestamps, amp, digital = out

            for ci in range(len(args.channels)):
                ring[ci].extend(amp[ci])
                hist_amp[ci].extend(amp[ci])
            hist_ts.extend(timestamps.tolist())

            # Marker epochs
            if marker is not None and digital is not None:
                for ev in marker.process(timestamps, digital):
                    if ev["type"] == "on":
                        print(f"  MARKER ON   epoch #{ev['n']:<4d} "
                              f"t={ev['ts']/sample_rate:.4f}s")
                    else:
                        _report_epoch(ev, sample_rate, args, hist_ts, hist_amp)

            # Periodic live spike-rate readout
            now = time.time()
            if now - last_report >= args.report_sec:
                last_report = now
                parts = []
                for ci, ch in enumerate(args.channels):
                    buf = np.array(ring[ci], dtype=np.float64)
                    if len(buf) < window_samples // 4:
                        parts.append(f"{ch}: buffering")
                        continue
                    spikes = detect_spikes(buf, sample_rate,
                                           threshold_rms=args.threshold_rms)
                    dur = len(buf) / sample_rate
                    rate = len(spikes) / dur if dur > 0 else 0.0
                    parts.append(f"{ch}: {rate:6.1f} sp/s")
                print(f"[{time.strftime('%H:%M:%S')}] " + " | ".join(parts))

    except KeyboardInterrupt:
        print("\nStopping ...")
    finally:
        cmd.set_runmode("stop")
        wave.close()
        cmd.close()
        print("Stopped and disconnected.")


def _report_epoch(ev, sample_rate, args, hist_ts, hist_amp):
    """Count spikes per channel inside a just-closed marker epoch."""
    start, end = ev["start"], ev["ts"]
    if start is None:
        print(f"  MARKER OFF  epoch #{ev['n']:<4d} (no matching ON edge seen)")
        return
    dur = (end - start) / sample_rate
    # Response window with latency offsets, in samples (like the offline counter).
    lo = start + int(args.left_ms / 1000.0 * sample_rate)
    hi = end + int(args.right_ms / 1000.0 * sample_rate)

    ts_arr = np.array(hist_ts, dtype=np.int64)
    mask = (ts_arr >= lo) & (ts_arr <= hi)
    counts = []
    if mask.any():
        win_dur = max((hi - lo) / sample_rate, 1e-9)
        for ci, ch in enumerate(args.channels):
            seg = np.array(hist_amp[ci], dtype=np.float64)[mask]
            if len(seg) < 8:
                counts.append(f"{ch}: n/a")
                continue
            n = len(detect_spikes(seg, sample_rate, threshold_rms=args.threshold_rms))
            counts.append(f"{ch}: {n} sp ({n/win_dur:.1f}/s)")
    else:
        counts = ["(epoch spikes not in history buffer — increase --hist-sec)"]

    print(f"  MARKER OFF  epoch #{ev['n']:<4d} dur={dur*1000:.1f}ms  "
          f"-> " + " | ".join(counts))


def _dump_first_frame(wave):
    """Print the raw bytes of one frame to help reverse-engineer the layout."""
    print("--dump-frame: waiting for a block ...")
    for _ in range(200):
        out = wave.read_frames()
        if out is not None:
            ts, amp, dig = out
            print(f"  first timestamp = {ts[0]}")
            print(f"  amp[:,0] (uV)   = {amp[:, 0]}")
            if dig is not None:
                print(f"  digital[0]      = 0x{int(dig[0]):04x} "
                      f"(bits: {int(dig[0]):016b})")
            return
        time.sleep(0.01)
    print("  (no block arrived to dump)")


def parse_args(argv):
    p = argparse.ArgumentParser(
        description="Phase 0 live spike + marker probe for Intan RHX.")
    p.add_argument("--host", default="127.0.0.1",
                   help="RHX TCP host (default 127.0.0.1).")
    p.add_argument("--cmd-port", type=int, default=5000)
    p.add_argument("--wave-port", type=int, default=5001)
    p.add_argument("--channels", nargs="+", default=["A-000"],
                   help="Amplifier channels, e.g. A-000 A-001 (native names).")
    p.add_argument("--marker-bit", type=int, default=1,
                   help="Digital-in bit for the photodiode marker "
                        "(DIGITAL-IN-2 == bit 1, the default).")
    p.add_argument("--no-digital", action="store_true",
                   help="Spikes only; skip digital-in/marker (isolation test).")
    p.add_argument("--digital-enable-cmd", default="set digitalin.tcpdataoutputenabled true",
                   help="Exact command RHX uses to enable digital-in TCP output. "
                        "VERIFY against your RHX build.")
    p.add_argument("--threshold-rms", type=float, default=4.0)
    p.add_argument("--window-ms", type=float, default=1000.0,
                   help="Sliding window for the live spike-rate readout.")
    p.add_argument("--report-sec", type=float, default=1.0,
                   help="How often to print the live spike-rate line.")
    p.add_argument("--left-ms", type=float, default=0.0,
                   help="Shift epoch start for spike counting (response latency).")
    p.add_argument("--right-ms", type=float, default=0.0,
                   help="Shift epoch end for spike counting.")
    p.add_argument("--hist-sec", type=float, default=5.0,
                   help="Seconds of history kept for per-epoch spike counting.")
    p.add_argument("--record", action="store_true",
                   help="Use runmode 'record' (save to disk) instead of 'run'.")
    p.add_argument("--dump-frame", action="store_true",
                   help="Print one raw frame's parsed values, then continue.")
    return p.parse_args(argv)


if __name__ == "__main__":
    run(parse_args(sys.argv[1:]))
