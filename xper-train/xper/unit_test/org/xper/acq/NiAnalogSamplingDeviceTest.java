package org.xper.acq;

import java.util.ArrayList;
import java.util.List;

import junit.framework.TestCase;

import org.xper.XperConfig;
import org.xper.NiTest;
import org.xper.acq.ni.NiAnalogSamplingDevice;
import org.xper.acq.vo.NiChannelSpec;
import org.xper.time.DefaultTimeUtil;
import org.xper.time.TimeUtil;

@NiTest
public class NiAnalogSamplingDeviceTest extends TestCase {
	public void test () {
		if (System.getProperty("ni_device") == null) {
			System.setProperty("ni_device", "Dev1");
		}
		
		List<String> libs = new ArrayList<String>();
		libs.add("xper");
		libs.add("xper-ni");
		new XperConfig("", libs);
		
		NiAnalogSamplingDevice d = new NiAnalogSamplingDevice();
		d.setDeviceString(System.getProperty("ni_device"));
		TimeUtil util = new DefaultTimeUtil();
		d.setLocalTimeUtil(util);
		
		NiChannelSpec spec0 = new NiChannelSpec();
		spec0.setChannel((short)0);
		spec0.setMaxValue(10.0);
		spec0.setMinValue(-10.0);
		
		NiChannelSpec spec1 = new NiChannelSpec();
		spec1.setChannel((short)1);
		spec1.setMaxValue(10.0);
		spec1.setMinValue(-10.0);
		
		ArrayList<NiChannelSpec> channels = new ArrayList<NiChannelSpec>();
		channels.add(spec0);
		channels.add(spec1);
		d.setInputChannels(channels);
	
		d.init();
		
		int len = 1000;	
		double tot = 0.0;
		for (int i= 0; i < len; i ++) {
			long prev = util.currentTimeMicros();
			long cur = d.scan();
			tot += cur - prev;
			//System.out.println(d.getData(0) + " " + d.getData(1));
			assertTrue(d.getData(0) <= spec0.getMaxValue() 
					&& d.getData(0) >= spec0.getMinValue());
			assertTrue(d.getData(1) <= spec1.getMaxValue() 
					&& d.getData(1) >= spec1.getMinValue());
		}
		
		d.destroy();
		
		System.out.println("Time for one DAQ: " + tot / len + " microseconds.");
	}
}
