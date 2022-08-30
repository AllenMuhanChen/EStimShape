package org.xper.acq;

import java.util.ArrayList;
import java.util.List;

import junit.framework.TestCase;

import org.apache.log4j.Logger;
import org.xper.XperConfig;
import org.xper.NiTest;
import org.xper.acq.ni.NiAnalogStreamingDevice;
import org.xper.acq.vo.NiChannelSpec;
import org.xper.time.DefaultTimeUtil;
import org.xper.time.TimeUtil;

@NiTest
public class NiAnalogStreamingDeviceTest extends TestCase {
	static Logger logger = Logger.getLogger(NiAnalogStreamingDeviceTest.class);
	
	public void test () {
		if (System.getProperty("ni_device") == null) {
			System.setProperty("ni_device", "Dev1");
		}
		
		TimeUtil timeUtil = new DefaultTimeUtil();
		
		List<String> libs = new ArrayList<String>();
		libs.add("xper");
		libs.add("xper-ni");
		new XperConfig("", libs);
		
		NiAnalogStreamingDevice device = new NiAnalogStreamingDevice();
		device.setDeviceString(System.getProperty("ni_device"));
		ArrayList<NiChannelSpec> channels = new ArrayList<NiChannelSpec>();
		
		NiChannelSpec spec0 = new NiChannelSpec();
		spec0.setChannel((short)0);
		spec0.setMaxValue(10.0);
		spec0.setMinValue(-10.0);
		channels.add(spec0);
		
		NiChannelSpec spec2 = new NiChannelSpec();
		spec2.setChannel((short)2);
		spec2.setMaxValue(10.0);
		spec2.setMinValue(-10.0);
		channels.add(spec2); 
		
		device.setInputChannels(channels);
		
		int rate = 25000;
		device.setMasterFreqency(rate);
		device.setBufferSize(40000);
		
		device.init();
		double tot = 0.0;
		
		device.start();
		double before = timeUtil.currentTimeMicros();
		for (int i = 0; i < 100000; i ++) {
			double[] result = device.scan();
			if (result != null) {
				assertEquals(0, result.length % 2);
				for (int j = 0; j < result.length/2; j ++) {
					assertTrue(result[j] <= spec0.getMaxValue() && result[j] >= spec0.getMinValue());
					assertTrue(result[j+1] <= spec2.getMaxValue() && result[j+1] >= spec2.getMinValue());
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
