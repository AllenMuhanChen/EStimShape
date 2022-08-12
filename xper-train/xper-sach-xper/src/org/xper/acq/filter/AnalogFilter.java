package org.xper.acq.filter;

import org.xper.Dependency;
import org.xper.exception.AcqException;

public class AnalogFilter extends AbstractDataFilter {

	@Dependency
	int recordEveryNSample = 1;
	@Dependency
	short channel;

	public void filter(short chan, int sampleIndex, int startSampleIndex,
			double value) {
		if (chan == channel) {
			if ((sampleIndex - startSampleIndex) % recordEveryNSample == 0) {
				record(chan, sampleIndex, value);
			}
		} else {
			throw new AcqException(
					"Data acquisition channel setup error: analog channel "
							+ channel + " is receiving data meant for channel "
							+ chan);
		}
	}

	public int getRecordEveryNSample() {
		return recordEveryNSample;
	}

	public void setRecordEveryNSample(int recordEveryNSample) {
		this.recordEveryNSample = recordEveryNSample;
	}

	public short getChannel() {
		return channel;
	}

	public void setChannel(short channel) {
		this.channel = channel;
	}

}
