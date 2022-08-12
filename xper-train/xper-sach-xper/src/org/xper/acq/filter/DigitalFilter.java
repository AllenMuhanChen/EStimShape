package org.xper.acq.filter;

import org.xper.Dependency;
import org.xper.acq.vo.DigitalChannel;
import org.xper.exception.AcqException;

public class DigitalFilter extends AbstractDataFilter {

	@Dependency
	protected double zeroThreshold;
	@Dependency
	protected double oneThreshold;
	@Dependency
	protected short channel;

	protected int status = -1;
	
	public void init () {
		status = -1;
	}

	public void filter(short chan, int sampleIndex, int startSampleIndex,
			double data) {
		if (chan != channel) {
			throw new AcqException(
					"Data acquisition channel setup error: digital channel "
							+ channel + " is receiving data meant for channel "
							+ chan);
		}
		switch (status) {
		case -1:
			if (data > oneThreshold) {
				status = 1;
				record(chan, sampleIndex, DigitalChannel.ONE);
			} else if (data < zeroThreshold) {
				status = 0;
				record(chan, sampleIndex, DigitalChannel.ZERO);
			}
			break;
		case 0:
			if (data > oneThreshold) {
				status = 1;
				record(chan, sampleIndex, DigitalChannel.ONE);
			} else if (data > zeroThreshold) {
				status = -1;
				record(chan, sampleIndex, DigitalChannel.ZERO);
			}
			break;
		case 1:
			if (data < zeroThreshold) {
				status = 0;
				record(chan, sampleIndex, DigitalChannel.ZERO);
			} else if (data < oneThreshold) {
				status = -1;
				record(chan, sampleIndex, DigitalChannel.ONE);
			}
			break;
		}
	}

	public double getZeroThreshold() {
		return zeroThreshold;
	}

	public void setZeroThreshold(double zeroThreshold) {
		this.zeroThreshold = zeroThreshold;
	}

	public double getOneThreshold() {
		return oneThreshold;
	}

	public void setOneThreshold(double oneThreshold) {
		this.oneThreshold = oneThreshold;
	}

	public short getChannel() {
		return channel;
	}

	public void setChannel(short channel) {
		this.channel = channel;
	}

}
