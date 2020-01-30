package org.xper.acq.filter;

import org.xper.acq.vo.DigitalChannel;
import org.xper.exception.AcqException;

public class HalfDigitalFilter extends DigitalFilter {

	double threshold;

	public void init() {
		status = -2;
		threshold = (zeroThreshold + oneThreshold) / 2.0;
	}

	public void filter(short chan, int sampleIndex, int startSampleIndex,
			double data) {
		if (chan != channel) {
			throw new AcqException(
					"Data acquisition channel setup error: half digital channel "
							+ channel + " is receiving data meant for channel "
							+ chan);
		}
		
		//int displayChannel = 1;
		
//		if (chan == displayChannel) 
//			System.out.println("data= " + data);
		
		switch (status) {
		case -2:
			if (data > threshold) {
				status = 2;
				record(chan, sampleIndex, DigitalChannel.UP);
			}
			break;
		case 2:
			if (data < threshold) {
				status = -2;
				record(chan, sampleIndex, DigitalChannel.DOWN);
			}
			break;
		}
	}

}
