package org.xper.acq;

import java.util.ArrayList;
import java.util.List;

import junit.framework.TestCase;

import org.xper.XperConfig;
import org.xper.NiTest;
import org.xper.acq.ni.NiAnalogSWOutDevice;
import org.xper.acq.vo.NiChannelSpec;
import org.xper.juice.AnalogJuice;
import org.xper.time.DefaultTimeUtil;

@NiTest
public class NiJuiceTest extends TestCase {
	public void test () {
		if (System.getProperty("ni_device") == null) {
			System.setProperty("ni_device", "Dev1");
		}
		
		List<String> libs = new ArrayList<String>();
		libs.add("xper");
		libs.add("xper-ni");
		new XperConfig("", libs);
		
		NiChannelSpec chan = new NiChannelSpec();
		chan.setChannel((short)0);
		chan.setMinValue(-10.0);
		chan.setMaxValue(10.0);
		
		NiAnalogSWOutDevice device = new NiAnalogSWOutDevice();
		device.setDeviceString(System.getProperty("ni_device"));
		ArrayList<NiChannelSpec> chans = new ArrayList<NiChannelSpec>();
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
