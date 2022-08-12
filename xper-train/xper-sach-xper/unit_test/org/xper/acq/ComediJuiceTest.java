package org.xper.acq;

import java.util.ArrayList;
import java.util.List;

import junit.framework.TestCase;

import org.xper.ComediTest;
import org.xper.XperConfig;
import org.xper.acq.comedi.ComediAnalogSWOutDevice;
import org.xper.acq.vo.ComediChannelSpec;
import org.xper.juice.AnalogJuice;
import org.xper.time.DefaultTimeUtil;

@ComediTest
public class ComediJuiceTest extends TestCase {
	public void test () {
		if (System.getProperty("comedi_device") == null) {
			System.setProperty("comedi_device", "/dev/comedi0");
		}
		
		List<String> libs = new ArrayList<String>();
		libs.add("xper");
		libs.add("xper-comedi");
		new XperConfig("", libs);
		
		ComediChannelSpec chan = new ComediChannelSpec();
		chan.setChannel((short)0);
		chan.setMinValue(-10.0);
		chan.setMaxValue(10.0);
		chan.setAref(ComediChannelSpec.AREF_DIFF);
		
		ComediAnalogSWOutDevice device = new ComediAnalogSWOutDevice();
		device.setDeviceString(System.getProperty("comedi_device"));
		ArrayList<ComediChannelSpec> chans = new ArrayList<ComediChannelSpec>();
		chans.add(chan);
		device.setOutputChannels(chans);
		device.init();
		
		AnalogJuice j = new AnalogJuice();
		j.setBonusDelay(100);
		j.setBonusProbability(0.5);
		j.setDelay(100);
		j.setReward(200);
		j.setDevice(device);
		j.setLocalTimeUtil(new DefaultTimeUtil());
		
		j.deliver();
		
		device.destroy();
	}
}
