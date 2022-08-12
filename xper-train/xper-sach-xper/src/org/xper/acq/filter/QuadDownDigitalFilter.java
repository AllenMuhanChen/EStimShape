package org.xper.acq.filter;

import org.xper.acq.vo.DigitalChannel;
import org.xper.exception.AcqException;

public class QuadDownDigitalFilter extends HalfDigitalFilter {
	public void filter(short chan, int sampleIndex, int startSampleIndex,
			double data) {
		if (chan != channel) {
			throw new AcqException(
					"Data acquisition channel setup error: quad up digital channel "
							+ channel + " is receiving data meant for channel "
							+ chan);
		}
		switch (status) {
		case -2:
			if (data > threshold) {
				status = 2;
			}
			break;
		case 2:
			if (data < threshold) {
				status = -2;
				record (chan, sampleIndex, DigitalChannel.PULSE_DOWN);
			}
			break;
	}
	}
}
