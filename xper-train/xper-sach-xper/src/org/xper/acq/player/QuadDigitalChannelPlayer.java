package org.xper.acq.player;

import java.util.List;

import org.xper.acq.vo.DigitalChannel;
import org.xper.acq.vo.DigitalChannel.EdgeType;
import org.xper.db.vo.AcqDataEntry;

@Deprecated
public abstract class QuadDigitalChannelPlayer extends DigitalChannelPlayer {

	public QuadDigitalChannelPlayer(List<AcqDataEntry> data, int chan) {
		super(data, chan);
	}

	@Override
	public int nextPulse(EdgeType edge, int endSampleIndex) {
		if (m_data.size() <= 0) return -1;

		int dest = -1;

		switch (edge) {
			case Up:
				if (getElemVal() != DigitalChannel.PULSE_UP) return -1;
				dest = getElemVal ();
				break;
			case Down:
				if (getElemVal() != DigitalChannel.PULSE_DOWN) return -1;
				dest = getElemVal () + 1;
				break;
			case Center:
				if (getElemVal() != DigitalChannel.PULSE_CENTER) return -1;
				dest = getElemVal ();
				break;
			default:
				return -1;
		}
		while (
			getData().getSampleInd() <= endSampleIndex && (
			getData().getChannel() != m_chan ||
			(int)(getData().getValue() + 0.5) != dest)) {
			if (!forward ()) return -1;
		}
		if (getData().getSampleInd() > endSampleIndex) {
			return -1;
		}
		return getData().getSampleInd();
	}
	
	@Override
	public int prevPulse(EdgeType edge, int startSampleIndex) {
		if (m_data.size() <= 0) return -1;

		int dest;

		switch (edge) {
			case Up:
				if (getElemVal() != DigitalChannel.PULSE_UP) return -1;
				dest = getElemVal ();
				break;
			case Down:
				if (getElemVal() != DigitalChannel.PULSE_DOWN) return -1;
				dest = getElemVal () + 1;
				break;
			case Center:
				if (getElemVal() != DigitalChannel.PULSE_CENTER) return -1;
				dest = getElemVal ();
				break;
			default:
				return -1;
		}
		while (
			getData().getSampleInd() >= startSampleIndex && (
			getData().getChannel() != m_chan ||
			(int)(getData().getValue() + 0.5) != dest)) {
			if (!rewind ()) return -1;
		}
		if (getData().getSampleInd() < startSampleIndex) {
			return -1;
		}
		return getData().getSampleInd();
	}
	
	public int lookAhead(EdgeType edge, int nextStart) {
		throw new RuntimeException("not implemented!");
	}
	
	protected abstract int getElemVal ();
}
