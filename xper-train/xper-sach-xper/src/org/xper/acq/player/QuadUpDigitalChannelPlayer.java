package org.xper.acq.player;

import java.util.List;

import org.xper.acq.vo.DigitalChannel;
import org.xper.db.vo.AcqDataEntry;

@Deprecated
public class QuadUpDigitalChannelPlayer extends QuadDigitalChannelPlayer {

	public QuadUpDigitalChannelPlayer(List<AcqDataEntry> data, int chan) {
		super(data, chan);
	}

	@Override
	protected int getElemVal() {
		return DigitalChannel.PULSE_UP;
	}

	@Override
	public boolean hasDown() {
		return false;
	}

	@Override
	public boolean hasCenter() {
		return false;
	}
}
