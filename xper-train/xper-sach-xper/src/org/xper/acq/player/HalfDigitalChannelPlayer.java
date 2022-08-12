package org.xper.acq.player;

import java.util.List;

import org.xper.acq.vo.DigitalChannel;
import org.xper.acq.vo.DigitalChannel.EdgeType;
import org.xper.db.vo.AcqDataEntry;

public class HalfDigitalChannelPlayer extends DigitalChannelPlayer {

	public HalfDigitalChannelPlayer(List<AcqDataEntry> data, int chan) {
		super(data, chan);
	}

	public int nextPulse(EdgeType edge, int endSampleIndex) {
		if (m_data.size() <= 0)
			return -1;

		// find the up edge
		int up_tstamp = -1;
		while (getData().getSampleInd() <= endSampleIndex
				&& (getData().getChannel() != m_chan || (int) (getData().getValue() + 0.5) != DigitalChannel.UP)) {
			if (!forward())
				return -1;
		}
		if (getData().getSampleInd() > endSampleIndex) {
			return -1;
		}
		up_tstamp = getData().getSampleInd();
		if (edge == DigitalChannel.EdgeType.Up)
			return up_tstamp;
		
		// find the down edge
		while (getData().getSampleInd() <= endSampleIndex
				&& (getData().getChannel() != m_chan || (int) (getData().getValue() + 0.5) != DigitalChannel.DOWN + 1)) {
			if (!forward())
				return -1;
		}
		if (getData().getSampleInd() > endSampleIndex) {
			return -1;
		}
		int down_tstamp = getData().getSampleInd();
		if (edge == DigitalChannel.EdgeType.Down)
			return down_tstamp;

		int pulse_tstamp = (int) ((double) (up_tstamp + down_tstamp) / 2.0 + 0.5);
		if (edge == DigitalChannel.EdgeType.Center)
			return pulse_tstamp;

		return -1;
	}

	public int prevPulse(EdgeType edge, int startSampleIndex) {
		if (m_data.size() <= 0)
			return -1;

		// find the down edge
		int down_tstamp = -1;
		while (getData().getSampleInd() >= startSampleIndex
				&& (getData().getChannel() != m_chan || (int) (getData().getValue() + 0.5) != DigitalChannel.DOWN + 1)) {
			if (!rewind())
				return -1;
		}
		if (getData().getSampleInd() < startSampleIndex) {
			return -1;
		}
		down_tstamp = getData().getSampleInd();
		if (edge == DigitalChannel.EdgeType.Down)
			return down_tstamp;
		
		// find the up edge
		while (getData().getSampleInd() >= startSampleIndex
				&& (getData().getChannel() != m_chan || (int) (getData().getValue() + 0.5) != DigitalChannel.UP)) {
			if (!rewind())
				return -1;
		}
		if (getData().getSampleInd() < startSampleIndex) {
			return -1;
		}
		int up_tstamp = getData().getSampleInd();
		if (edge == DigitalChannel.EdgeType.Up)
			return up_tstamp;

		int pulse_tstamp = (int) ((double) (up_tstamp + down_tstamp) / 2.0 + 0.5);
		if (edge == DigitalChannel.EdgeType.Center)
			return pulse_tstamp;

		return -1;

	}
	
	public int lookAhead(EdgeType edgeType) {
		if (m_data.size() <= 0)
			return -1;
		
		int dest = DigitalChannel.DOWN + 1;
		if (edgeType == DigitalChannel.EdgeType.Up) dest = DigitalChannel.UP;
		
		int cur = getPosition();
		int j = 0;
		while (getData(cur+j).getSampleInd() < getEndSampleIndex()
				&& (getData(cur+j).getChannel() != m_chan || (int) (getData(cur+j).getValue() + 0.5) != dest)) {
			j ++;
		}
		if (getData(cur+j).getSampleInd() == getEndSampleIndex()) {
			return -1;
		} else {
			return getData(cur+j).getSampleInd();
		}
	}

}
