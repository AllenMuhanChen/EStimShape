package org.xper.acq.filter;

import org.xper.acq.vo.DigitalChannel;
import org.xper.exception.AcqException;

public class QuadCenterDigitalFilter extends HalfDigitalFilter {

	int m_up_ind = -1;

	public void filter(short chan, int sampleIndex, int startSampleIndex,
			double data) {
		if (chan != channel) {
			throw new AcqException(
					"Data acquisition channel setup error: quad center digital channel "
							+ channel + " is receiving data meant for channel "
							+ chan);
		}
		switch (status) {
		case -2:
			if (data > threshold) {
				status = 2;
				m_up_ind = sampleIndex;
			}
			break;
		case 2:
			if (data < threshold) {
				status = -2;
				if (m_up_ind != -1) {
					record(chan, (int) ((sampleIndex + m_up_ind) / 2.0 + 0.5),
							DigitalChannel.PULSE_CENTER);
				}
			}
			break;
		}
	}

}
