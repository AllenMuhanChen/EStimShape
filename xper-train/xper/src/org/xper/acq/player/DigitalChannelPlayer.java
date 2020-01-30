package org.xper.acq.player;

import java.util.List;

import org.xper.acq.vo.DigitalChannel;
import org.xper.acq.vo.DigitalChannel.EdgeType;
import org.xper.db.vo.AcqDataEntry;

public class DigitalChannelPlayer extends AnalogDataPlayer implements
		DigitalPlayer {
	int m_chan;
	
	public DigitalChannelPlayer(List<AcqDataEntry> data, int chan) {
		super(data);
		m_chan = chan;
	}

	public int getType() {
		if (m_data.size() <= 0)
			return -1;
		reset();

		do {
			if (getData().getChannel() == m_chan) {
				return (int) (getData().getValue() + 0.5);
			}
		} while (forward());

		reset();
		return -1;
	}

	public boolean hasCenter() {
		return true;
	}

	public boolean hasDown() {
		return true;
	}

	public boolean hasUp() {
		return true;
	}

	public int nextPulse(EdgeType edge, int endSampleIndex) {
		if (m_data.size() <= 0)
			return -1;

		int upIndex = -1;
		int downIndex = -1;
		int zeroIndex = -1;
		int oneIndex = -1;

		// Find the last ZERO before a ONE
		while (getData().getSampleInd() <= endSampleIndex
				&& (getData().getChannel() != m_chan || (int) (getData().getValue() + 0.5) != DigitalChannel.ONE)) {
			// Tracking the ZERO index
			if (getData().getChannel() == m_chan) {
				zeroIndex = getData().getSampleInd();
			}
			if (!forward())
				return -1;
		}
		if (getData().getSampleInd() > endSampleIndex) {
			return -1;
		}
		// Got a ONE
		upIndex = (int) ((double) (zeroIndex + getData().getSampleInd()) / 2.0 + 0.5);
		if (edge == DigitalChannel.EdgeType.Up)
			return upIndex;
		while (getData().getSampleInd() <= endSampleIndex
				&& (getData().getChannel() != m_chan || (int) (getData().getValue() + 0.5) != DigitalChannel.ZERO)) {
			// Tracking the ONE index
			if (getData().getChannel() == m_chan) {
				oneIndex = getData().getSampleInd();
			}
			if (!forward())
				return -1;
		}
		if (getData().getSampleInd() > endSampleIndex) {
			return -1;
		}
		// Got ZERO
		downIndex = (int) ((double) (oneIndex + getData().getSampleInd()) / 2.0 + 0.5);
		if (edge == DigitalChannel.EdgeType.Down)
			return downIndex;
		int pulseIndex = (int) ((double) (upIndex + downIndex) / 2.0 + 0.5);
		if (edge == DigitalChannel.EdgeType.Center)
			return pulseIndex;

		return -1;
	}

	/**
	 * Go back from current position, try to find edge whose position is after startSampleIndex.
	 */
	public int prevPulse(EdgeType edge, int startSampleIndex) {
		if (m_data.size() <= 0)
			return -1;

		int upIndex = -1;
		int downIndex = -1;
		int zeroIndex = -1;
		int oneIndex = -1;

		while (getData().getSampleInd() >= startSampleIndex
				&& (getData().getChannel() != m_chan || (int) (getData().getValue() + 0.5) != DigitalChannel.ONE)) {
			// Tracking the ZERO index
			if (getData().getChannel() == m_chan) {
				zeroIndex = getData().getSampleInd();
			}
			if (!rewind())
				return -1;
		}
		if (getData().getSampleInd() < startSampleIndex) {
			return -1;
		}
		// Get a ONE
		downIndex = (int) ((double) (zeroIndex + getData().getSampleInd()) / 2.0 + 0.5);
		if (edge == DigitalChannel.EdgeType.Down)
			return downIndex;

		while (getData().getSampleInd() >= startSampleIndex
				&& (getData().getChannel() != m_chan || (int) (getData().getValue() + 0.5) != DigitalChannel.ZERO)) {
			// Tracking the ONE index
			if (getData().getChannel() == m_chan) {
				oneIndex = getData().getSampleInd();
			}
			if (!rewind())
				return -1;
		}
		if (getData().getSampleInd() < startSampleIndex) {
			return -1;
		}
		// Get a ZERO
		upIndex = (int) ((double) (oneIndex + getData().getSampleInd()) / 2.0 + 0.5);
		if (edge == DigitalChannel.EdgeType.Up)
			return upIndex;

		int pulseIndex = (int) ((double) (upIndex + downIndex) / 2.0 + 0.5);
		if (edge == DigitalChannel.EdgeType.Center)
			return pulseIndex;

		return -1;

	}

	public int lookAhead(EdgeType down) {
		return getData().getSampleInd();
	}
}
