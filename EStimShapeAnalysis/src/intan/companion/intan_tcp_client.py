"""
Intan RHX TCP Client
====================
Manages command and waveform socket connections to the Intan RHX software.
Handles protocol-level details: block parsing, channel discovery, and command I/O.

Protocol reference: IntanRHX_TCPDocumentation.pdf (v3.5.0)
- Command socket (default 5000): text-based get/set/execute commands
- Waveform socket (default 5001): binary data blocks
  - Each block: 4-byte magic (0x2ef07a08) + 128 frames
  - Each frame: 4-byte int32 timestamp + 2-byte uint16 per enabled channel
  - Sample to µV: 0.195 * (raw - 32768)
"""

import socket
import struct
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict

import numpy as np


MAGIC_NUMBER = 0x2ef07a08
FRAMES_PER_BLOCK = 128
COMMAND_BUFFER_SIZE = 4096
MICROVOLTS_PER_BIT = 0.195
SAMPLE_OFFSET = 32768


@dataclass
class ChannelInfo:
    """Metadata for a single amplifier channel."""
    native_name: str       # e.g. "A-010"
    port: str              # e.g. "A"
    channel_number: int    # e.g. 10
    tcp_enabled: bool = False
    custom_name: str = ""

    @property
    def display_name(self) -> str:
        return self.custom_name if self.custom_name else self.native_name


class IntanTCPClient:
    """
    Manages TCP connections to the Intan RHX software.

    Usage:
        client = IntanTCPClient()
        client.connect_command('127.0.0.1', 5000)
        client.connect_waveform('127.0.0.1', 5001)

        sample_rate = client.get_sample_rate()
        channels = client.discover_enabled_channels()
        client.start_running()

        # In a loop:
        blocks = client.read_waveform_blocks(n_channels=len(channels))

        client.stop_running()
        client.disconnect()
    """

    def __init__(self):
        self._cmd_socket: Optional[socket.socket] = None
        self._wave_socket: Optional[socket.socket] = None
        self._sample_rate: Optional[float] = None
        self._controller_type: Optional[str] = None

    # ── Connection management ────────────────────────────────────────

    def connect_command(self, host: str = '127.0.0.1', port: int = 5000,
                        timeout: float = 5.0):
        """Connect to the RHX command socket."""
        self._cmd_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._cmd_socket.settimeout(timeout)
        self._cmd_socket.connect((host, port))

    def connect_waveform(self, host: str = '127.0.0.1', port: int = 5001,
                         timeout: float = 5.0):
        """Connect to the RHX waveform data socket."""
        self._wave_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._wave_socket.settimeout(timeout)
        self._wave_socket.connect((host, port))

    def disconnect(self):
        """Close both sockets."""
        for sock in (self._cmd_socket, self._wave_socket):
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
        self._cmd_socket = None
        self._wave_socket = None

    @property
    def is_command_connected(self) -> bool:
        return self._cmd_socket is not None

    @property
    def is_waveform_connected(self) -> bool:
        return self._wave_socket is not None

    # ── Command I/O ──────────────────────────────────────────────────

    def send_command(self, command: str) -> str:
        """Send a text command and return the response string."""
        if self._cmd_socket is None:
            raise ConnectionError("Command socket not connected")
        self._cmd_socket.sendall(command.encode('utf-8'))
        time.sleep(0.02)  # small delay for RHX to process
        try:
            response = self._cmd_socket.recv(COMMAND_BUFFER_SIZE).decode('utf-8')
        except socket.timeout:
            response = ""
        return response.strip()

    def get(self, parameter: str) -> str:
        """Send a 'get' command and return the value portion of the response."""
        resp = self.send_command(f'get {parameter}')
        # Response format: "Return: ParameterName Value"
        if resp.startswith("Return:"):
            # Strip "Return: " prefix, then everything up to the last space
            # is the parameter echo — the rest is the value
            parts = resp.split()
            if len(parts) >= 3:
                return ' '.join(parts[2:])
            elif len(parts) == 2:
                return parts[1]
        return resp

    def set(self, parameter: str, value: str) -> str:
        """Send a 'set' command."""
        return self.send_command(f'set {parameter} {value}')

    def execute(self, action: str) -> str:
        """Send an 'execute' command."""
        return self.send_command(f'execute {action}')

    # ── System queries ───────────────────────────────────────────────

    def get_sample_rate(self) -> float:
        """Query and cache the sample rate from RHX."""
        val = self.get('sampleratehertz')
        self._sample_rate = float(val)
        return self._sample_rate

    def get_controller_type(self) -> str:
        """Query controller type."""
        self._controller_type = self.get('type')
        return self._controller_type

    def get_run_mode(self) -> str:
        """Query current run mode (Run, Stop, Record)."""
        return self.get('runmode')

    # ── Run control ──────────────────────────────────────────────────

    def stop_running(self):
        """Stop the controller if running."""
        mode = self.get_run_mode()
        if 'Stop' not in mode:
            self.set('runmode', 'stop')
            time.sleep(0.1)

    def start_running(self):
        """Start the controller running."""
        self.set('runmode', 'run')

    # ── Channel discovery ────────────────────────────────────────────

    def get_port_channel_count(self, port: str) -> int:
        """Get number of amplifier channels present on a port (A-H)."""
        val = self.get(f'{port.lower()}.numberamplifierchannels')
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    def is_channel_tcp_enabled(self, channel_name: str) -> bool:
        """Check if a channel has TCP wideband output enabled."""
        val = self.get(f'{channel_name.lower()}.tcpdataoutputenabled')
        return val.lower() == 'true'

    def discover_enabled_channels(self) -> List[ChannelInfo]:
        """
        Scan all ports and return channels that have TCP data output enabled.
        This matches the user's workflow: they enable channels in RHX first,
        then this app discovers what's available.
        """
        enabled = []
        ports = ['A', 'B', 'C', 'D']

        # Check if 1024-ch controller (ports E-H)
        ctrl_type = self.get_controller_type()
        if '1024' in ctrl_type or 'USB3' in ctrl_type:
            ports.extend(['E', 'F', 'G', 'H'])

        for port in ports:
            n_channels = self.get_port_channel_count(port)
            if n_channels == 0:
                continue

            for ch_num in range(n_channels):
                name = f'{port}-{ch_num:03d}'
                if self.is_channel_tcp_enabled(name):
                    info = ChannelInfo(
                        native_name=name,
                        port=port,
                        channel_number=ch_num,
                        tcp_enabled=True,
                    )
                    enabled.append(info)

        return enabled

    def discover_enabled_channels_fast(self, ports: List[str] = None,
                                        max_channel: int = 128) -> List[ChannelInfo]:
        """
        Faster channel discovery using semicolon-batched commands.
        Queries TCP enabled status for all channels on specified ports.

        For very large channel counts, this is still sequential but
        minimizes per-command overhead.
        """
        if ports is None:
            ports = ['A', 'B', 'C', 'D']

        enabled = []
        for port in ports:
            n_channels = self.get_port_channel_count(port)
            if n_channels == 0:
                continue

            for ch_num in range(min(n_channels, max_channel)):
                name = f'{port}-{ch_num:03d}'
                if self.is_channel_tcp_enabled(name):
                    info = ChannelInfo(
                        native_name=name,
                        port=port,
                        channel_number=ch_num,
                        tcp_enabled=True,
                    )
                    enabled.append(info)

        return enabled

    # ── Waveform data reading ────────────────────────────────────────

    def read_waveform_data(self, n_channels: int,
                           max_bytes: int = 0) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Read available waveform data from the TCP waveform socket.

        Each block: 4-byte magic + 128 * (4-byte timestamp + n_channels * 2-byte sample)

        Args:
            n_channels: Number of TCP-enabled channels (determines frame size)
            max_bytes: Maximum bytes to read (0 = read whatever is available)

        Returns:
            (timestamps, data) where:
                timestamps: 1D array of int32 timestamp values
                data: 2D array of shape (n_channels, n_samples) in microvolts
            or None if no data available.
        """
        if self._wave_socket is None:
            raise ConnectionError("Waveform socket not connected")

        # Calculate block size
        bytes_per_frame = 4 + (n_channels * 2)  # timestamp + samples
        bytes_per_block = 4 + (FRAMES_PER_BLOCK * bytes_per_frame)  # magic + frames

        # Read available data
        self._wave_socket.setblocking(False)
        chunks = []
        total_read = 0
        try:
            while True:
                if max_bytes > 0 and total_read >= max_bytes:
                    break
                chunk = self._wave_socket.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                total_read += len(chunk)
        except BlockingIOError:
            pass  # No more data available right now
        except socket.error:
            pass
        finally:
            self._wave_socket.setblocking(True)

        if not chunks:
            return None

        raw_data = b''.join(chunks)

        # Trim to complete blocks
        n_complete_blocks = len(raw_data) // bytes_per_block
        if n_complete_blocks == 0:
            return None

        raw_data = raw_data[:n_complete_blocks * bytes_per_block]

        return self._parse_waveform_blocks(raw_data, n_channels,
                                            n_complete_blocks, bytes_per_block,
                                            bytes_per_frame)

    def read_waveform_data_blocking(self, n_channels: int,
                                     num_blocks: int) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Read exactly num_blocks of waveform data (blocking).

        Returns:
            (timestamps, data) where data is (n_channels, n_samples) in µV.
        """
        if self._wave_socket is None:
            raise ConnectionError("Waveform socket not connected")

        bytes_per_frame = 4 + (n_channels * 2)
        bytes_per_block = 4 + (FRAMES_PER_BLOCK * bytes_per_frame)
        total_bytes = num_blocks * bytes_per_block

        raw_data = b''
        while len(raw_data) < total_bytes:
            chunk = self._wave_socket.recv(total_bytes - len(raw_data))
            if not chunk:
                break
            raw_data += chunk

        n_complete_blocks = len(raw_data) // bytes_per_block
        if n_complete_blocks == 0:
            return None

        raw_data = raw_data[:n_complete_blocks * bytes_per_block]
        return self._parse_waveform_blocks(raw_data, n_channels,
                                            n_complete_blocks, bytes_per_block,
                                            bytes_per_frame)

    def _parse_waveform_blocks(self, raw_data: bytes, n_channels: int,
                                n_blocks: int, bytes_per_block: int,
                                bytes_per_frame: int
                                ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Parse raw TCP waveform bytes into timestamps and µV data.

        Returns:
            timestamps: 1D int32 array, length n_blocks * 128
            data: 2D float64 array, shape (n_channels, n_blocks * 128)
        """
        total_frames = n_blocks * FRAMES_PER_BLOCK
        timestamps = np.zeros(total_frames, dtype=np.int32)
        data = np.zeros((n_channels, total_frames), dtype=np.float64)

        idx = 0
        frame_idx = 0

        for block in range(n_blocks):
            # Read and verify magic number
            magic = struct.unpack_from('<I', raw_data, idx)[0]
            idx += 4
            if magic != MAGIC_NUMBER:
                raise ValueError(
                    f"Invalid magic number at block {block}: "
                    f"0x{magic:08x} (expected 0x{MAGIC_NUMBER:08x})"
                )

            for frame in range(FRAMES_PER_BLOCK):
                # Timestamp: signed 32-bit int
                timestamps[frame_idx] = struct.unpack_from('<i', raw_data, idx)[0]
                idx += 4

                # Channel samples: unsigned 16-bit ints
                for ch in range(n_channels):
                    raw_sample = struct.unpack_from('<H', raw_data, idx)[0]
                    idx += 2
                    data[ch, frame_idx] = MICROVOLTS_PER_BIT * (raw_sample - SAMPLE_OFFSET)

                frame_idx += 1

        return timestamps, data

    def flush_waveform_buffer(self):
        """Discard any queued data on the waveform socket."""
        if self._wave_socket is None:
            return
        self._wave_socket.setblocking(False)
        try:
            while True:
                chunk = self._wave_socket.recv(65536)
                if not chunk:
                    break
        except (BlockingIOError, socket.error):
            pass
        finally:
            self._wave_socket.setblocking(True)
