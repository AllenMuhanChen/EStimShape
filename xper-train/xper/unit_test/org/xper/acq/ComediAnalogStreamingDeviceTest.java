package org.xper.acq;

import java.util.ArrayList;
import java.util.List;

import junit.framework.TestCase;

import org.apache.log4j.Logger;
import org.xper.ComediTest;
import org.xper.XperConfig;
import org.xper.acq.comedi.ComediAnalogStreamingDevice;
import org.xper.acq.vo.ComediChannelSpec;
import org.xper.time.DefaultTimeUtil;
import org.xper.time.TimeUtil;

@ComediTest
public class ComediAnalogStreamingDeviceTest extends TestCase {
	static Logger logger = Logger.getLogger(ComediAnalogStreamingDeviceTest.class);
	
	public void test () {
		if (System.getProperty("comedi_device") == null) {
			System.setProperty("comedi_device", "/dev/comedi0");
		}
		
		TimeUtil timeUtil = new DefaultTimeUtil();
		
		List<String> libs = new ArrayList<String>();
		libs.add("xper");
		libs.add("xper-comedi");
		new XperConfig("", libs);
		
		ComediAnalogStreamingDevice device = new ComediAnalogStreamingDevice();
		device.setDeviceString(System.getProperty("comedi_device"));
		ArrayList<ComediChannelSpec> channels = new ArrayList<ComediChannelSpec>();
		
		for (short i = 0; i < 8; i ++) {
			ComediChannelSpec spec = new ComediChannelSpec();
			spec.setChannel((short)i);
			spec.setMaxValue(10.0);
			spec.setMinValue(-10.0);
			spec.setAref(ComediChannelSpec.AREF_DIFF);
			channels.add(spec);
		}
		
		device.setInputChannels(channels);
		
		int rate = 25000;
		device.setMasterFreqency(rate);
		device.setBufferSize(32000);
		
		device.init();
		double tot = 0.0;
		
		int channelIndex = 0;
		
		device.start();
		int rep = 10000;
		double before = timeUtil.currentTimeMicros();
		for (int i = 0; i < rep; i ++) {
			double[] result = device.scan();
			if (result != null) {
				//logger.info(result.length + " samples read.");
				for (int j = 0; j < result.length; j ++) {
					ComediChannelSpec spec = channels.get(channelIndex);
					assertTrue(result[j] <= spec.getMaxValue() && result[j] >= spec.getMinValue());
					channelIndex ++;
					if (channelIndex == channels.size()) {
						channelIndex = 0;
					}
				}
				tot += result.length;
			}
		}
		device.stop();
		double after = timeUtil.currentTimeMicros();
		
		double actualRate = tot / ((after - before) / 1000000.0) / (double)channels.size();
		
		device.destroy();
		
		logger.info("Rate: " + actualRate);
		assertTrue(Math.abs((rate - actualRate)/rate) <= 0.05);
	}  
}
