package org.xper.acq.ni;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.DoubleBuffer;
import java.util.HashMap;
import java.util.List;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;

import org.xper.Dependency;
import org.xper.acq.device.AcqSamplingDevice;
import org.xper.acq.vo.NiChannelSpec;
import org.xper.exception.NiException;
import org.xper.time.TimeUtil;

/**
 * Software timing analog input device.
 * 
 * @author John
 *
 */
public class NiAnalogSamplingDevice implements AcqSamplingDevice {

	@Dependency
	TimeUtil localTimeUtil;
	@Dependency
	String deviceString;
	@Dependency
	List<NiChannelSpec> inputChannels;
	
	ByteBuffer handle;
	ByteBuffer buf;
	DoubleBuffer dataView;
	HashMap<Integer, Integer> channelDataMap = new HashMap<Integer, Integer>();
	
	public double getData(int channel) {
		int i = channelDataMap.get(new Integer(channel)).intValue();
		return dataView.get(i);
	}
	
	@PostConstruct
	public void init () {
		if (deviceString == null) {
			throw new NiException("Device name is null.");
		}
		if (inputChannels == null || inputChannels.size() == 0) {
			throw new NiException("Input channels list is null or empty.");
		}
		buf = ByteBuffer.allocateDirect(
				inputChannels.size() * Double.SIZE / 8).order(
				ByteOrder.nativeOrder());
		dataView = buf.asDoubleBuffer();
		
		handle = nCreateTask(inputChannels.size());
		for (int i = 0; i < inputChannels.size(); i ++) {
			NiChannelSpec spec = inputChannels.get(i);
			nCreateChannels(handle, deviceString + "/ai" + spec.getChannel(), spec.getMinValue(), spec.getMaxValue());
			channelDataMap.put(new Integer(spec.getChannel()), new Integer(i));
		}
	}
	
	@PreDestroy
	public void destroy () {
		nDestroy(handle);
	}
	
	native ByteBuffer nCreateTask (int nChannels);
	native void nDestroy(ByteBuffer handle);
	native void nCreateChannels (ByteBuffer handle, String channel, double minValue, double MaxValue);
	native void nScan (ByteBuffer handle, ByteBuffer buf);

	public long scan() {
		nScan(handle, buf);
		return localTimeUtil.currentTimeMicros();
	}

	public TimeUtil getLocalTimeUtil() {
		return localTimeUtil;
	}

	public void setLocalTimeUtil(TimeUtil localTimeUtil) {
		this.localTimeUtil = localTimeUtil;
	}

	public List<NiChannelSpec> getInputChannels() {
		return inputChannels;
	}

	public void setInputChannels(List<NiChannelSpec> inputChannels) {
		this.inputChannels = inputChannels;
	}

	public String getDeviceString() {
		return deviceString;
	}

	public void setDeviceString(String deviceString) {
		this.deviceString = deviceString;
	}
}
