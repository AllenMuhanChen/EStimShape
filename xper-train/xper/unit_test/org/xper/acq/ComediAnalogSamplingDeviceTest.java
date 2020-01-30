package org.xper.acq;

import java.util.ArrayList;
import java.util.List;

import junit.framework.TestCase;

import org.xper.ComediTest;
import org.xper.XperConfig;
import org.xper.acq.comedi.ComediAnalogSamplingDevice;
import org.xper.acq.vo.ComediChannelSpec;
import org.xper.time.DefaultTimeUtil;
import org.xper.time.TimeUtil;

@ComediTest
public class ComediAnalogSamplingDeviceTest extends TestCase {
	public void test () {
		if (System.getProperty("comedi_device") == null) {
			System.setProperty("comedi_device", "/dev/comedi0");
		}
		
		List<String> libs = new ArrayList<String>();
		libs.add("xper");
		libs.add("xper-comedi");
		new XperConfig("", libs);
		
		ComediAnalogSamplingDevice d = new ComediAnalogSamplingDevice();
		d.setDeviceString(System.getProperty("comedi_device"));
		TimeUtil util = new DefaultTimeUtil();
		d.setLocalTimeUtil(util);
		
		ComediChannelSpec spec0 = new ComediChannelSpec();
		spec0.setChannel((short)0);
		spec0.setMaxValue(10.0);
		spec0.setMinValue(-10.0);
		spec0.setAref(ComediChannelSpec.AREF_DIFF);
		
		ComediChannelSpec spec1 = new ComediChannelSpec();
		spec1.setChannel((short)1);
		spec1.setMaxValue(10.0);
		spec1.setMinValue(-10.0);
		spec1.setAref(ComediChannelSpec.AREF_DIFF);
		
		ArrayList<ComediChannelSpec> channels = new ArrayList<ComediChannelSpec>();
		channels.add(spec0);
		channels.add(spec1);
		d.setInputChannels(channels);
	
		d.init();
		
		int len = 10;	
		double tot = 0.0;
		for (int i= 0; i < len; i ++) {
			long prev = util.currentTimeMicros();
			long cur = d.scan();
			tot += cur - prev;
			System.out.println(d.getData(0) + " " + d.getData(1));
			assertTrue(d.getData(0) <= spec0.getMaxValue() 
					&& d.getData(0) >= spec0.getMinValue());
			assertTrue(d.getData(1) <= spec1.getMaxValue() 
					&& d.getData(1) >= spec1.getMinValue());
		}
		
		d.destroy();
		
		System.out.println("Time for one DAQ: " + tot / len + " microseconds.");
	}
}
