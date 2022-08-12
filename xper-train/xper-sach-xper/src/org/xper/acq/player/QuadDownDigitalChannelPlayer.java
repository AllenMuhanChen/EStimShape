package org.xper.acq.player;

import java.util.List;

import org.xper.acq.vo.DigitalChannel;
import org.xper.db.vo.AcqDataEntry;

@Deprecated
public class QuadDownDigitalChannelPlayer extends QuadDigitalChannelPlayer {

	public QuadDownDigitalChannelPlayer(List<AcqDataEntry> data, int chan) {
		super(data, chan);
	}

	@Override
	protected int getElemVal() {
		return DigitalChannel.PULSE_DOWN;
	}

	@Override
	public boolean hasUp() {
		return false;
	}

	@Override
	public boolean hasCenter() {
		return false;
	}
}
