package org.xper.acq.player;

import java.util.List;

import org.xper.acq.vo.DigitalChannel;
import org.xper.db.vo.AcqDataEntry;

@Deprecated
public class QuadCenterDigitalChannelPlayer extends QuadDigitalChannelPlayer {

	public QuadCenterDigitalChannelPlayer(List<AcqDataEntry> data, int chan) {
		super(data, chan);
	}

	@Override
	protected int getElemVal() {
		return DigitalChannel.PULSE_CENTER;
	}
	
	@Override
	public boolean hasDown() {
		return false;
	}

	@Override
	public boolean hasUp() {
		return false;
	}
}
