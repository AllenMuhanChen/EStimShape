package org.xper.acq.player;

import java.util.List;

import org.xper.db.vo.AcqDataEntry;

public class AnalogChannelPlayer extends AnalogDataPlayer {
	int m_chan;

	public AnalogChannelPlayer(List<AcqDataEntry> data, int chan) {
		super(data);
		m_chan = chan;
	}

	public boolean seekBeginWith(int sampleIndex) {
		if (!super.seekBeginWith(sampleIndex)) {
			return false;
		}
		if (getData().getChannel() == m_chan) {
			return true;
		}
		return forward();
	}

	public boolean seekEndWith(int sampleIndex) {
		if (!super.seekEndWith(sampleIndex)) {
			return false;
		}
		if (getData().getChannel() == m_chan) {
			return true;
		}
		return rewind();
	}

	/**
	 * Forward to the next data record of this channel.
	 */
	public boolean forward() {
		if (!super.forward()) {
			return false;
		}
		while (getData().getChannel() != m_chan) {
			if (!super.forward()) {
				return false;
			}
		}
		return true;
	}
	
	/**
	 * Rewind to the prior data record of this channel
	 */
	public boolean rewind () {
		if (!super.rewind()) {
			return false;
		}
		while (getData().getChannel() != m_chan) {
			if (!super.rewind()) {
				return false;
			}
		}
		return true;
	}
}
