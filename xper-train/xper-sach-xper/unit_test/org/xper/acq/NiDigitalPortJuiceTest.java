package org.xper.acq;

import java.util.ArrayList;
import java.util.List;

import junit.framework.TestCase;

import org.xper.XperConfig;
import org.xper.NiTest;
import org.xper.acq.ni.NiDigitalPortOutDevice;
import org.xper.juice.DigitalPortJuice;

@NiTest
public class NiDigitalPortJuiceTest extends TestCase {
	public void test () {
		if (System.getProperty("ni_device") == null) {
			System.setProperty("ni_device", "Dev1");
		}
		
		List<String> libs = new ArrayList<String>();
		libs.add("xper");
		libs.add("xper-ni");
		new XperConfig("", libs);
		
		NiDigitalPortOutDevice device = new NiDigitalPortOutDevice();
		device.setDeviceString(System.getProperty("ni_device"));
		ArrayList<Integer> chans = new ArrayList<Integer>();
		chans.add(new Integer(0));
		device.setPorts(chans);
		device.init();
		
		DigitalPortJuice j = new DigitalPortJuice();
		j.setReward(200);
		j.setDevice(device);
		
		j.deliver();
		
		device.destroy();
	}
}
