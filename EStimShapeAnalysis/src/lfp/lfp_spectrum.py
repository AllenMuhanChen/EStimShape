from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
from scipy.signal import welch


Spectrum = Tuple[np.ndarray, np.ndarray]  # (frequencies, power)


@dataclass
class LFPSpectrum:
    sample_rate: float
    nperseg: int = 512  # ~0.5 Hz resolution at 1 kHz LFP sample rate
    noverlap: Optional[int] = None  # defaults to nperseg // 2
    window: str = 'hann'

    def compute(self, lfp) -> Union[
        Spectrum,
        List[Spectrum],
        Dict[int, Optional[Dict[str, Spectrum]]]
    ]:
        """
        Compute power spectrum from LFP data. Accepts flexible input formats:

        - np.ndarray: single waveform -> (frequencies, power)
        - List[np.ndarray]: list of waveforms -> List[(frequencies, power)]
        - Dict[taskId, Dict[Channel, np.ndarray]]: parser output ->
            Dict[taskId, Dict[Channel, (frequencies, power)]]
        """
        if isinstance(lfp, np.ndarray):
            return self._compute_one(lfp)
        elif isinstance(lfp, list):
            return [self._compute_one(x) for x in lfp]
        elif isinstance(lfp, dict):
            return self._compute_dict(lfp)
        else:
            raise TypeError(f"Unsupported input type: {type(lfp)}")

    def _compute_one(self, waveform: np.ndarray) -> Spectrum:
        freqs, power = welch(
            waveform,
            fs=self.sample_rate,
            nperseg=min(self.nperseg, len(waveform)),
            noverlap=self.noverlap,
            window=self.window,
        )
        return freqs, power

    def _compute_dict(
        self, lfp_by_channel_by_task_id: Dict[int, Optional[Dict[str, np.ndarray]]]
    ) -> Dict[int, Optional[Dict[str, Spectrum]]]:
        result = {}
        for task_id, channels_dict in lfp_by_channel_by_task_id.items():
            if channels_dict is None:
                result[task_id] = None
                continue
            result[task_id] = {
                channel: self._compute_one(waveform)
                for channel, waveform in channels_dict.items()
            }
        return result