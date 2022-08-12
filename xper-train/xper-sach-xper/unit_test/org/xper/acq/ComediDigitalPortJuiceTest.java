package org.xper.acq;

import java.util.ArrayList;
import java.util.List;

import junit.framework.TestCase;

import org.xper.ComediTest;
import org.xper.XperConfig;
import org.xper.acq.comedi.ComediDigitalPortOutDevice;
import org.xper.juice.DigitalPortJuice;

@ComediTest
public class ComediDigitalPortJuiceTest extends TestCase {
	public void test () {
		if (System.getProperty("comedi_device") == null) {
			System.setProperty("comedi_device", "/dev/comedi0");
		}
		
		List<String> libs = new ArrayList<String>();
		libs.add("xper");
		libs.add("xper-comedi");
		new XperConfig("", libs);
		
		ComediDigitalPortOutDevice device = new ComediDigitalPortOutDevice();
		device.setDeviceString(System.getProperty("comedi_device"));
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
