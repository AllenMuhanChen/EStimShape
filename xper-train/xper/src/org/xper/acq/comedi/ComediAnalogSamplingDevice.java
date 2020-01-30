package org.xper.acq.comedi;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.DoubleBuffer;
import java.util.HashMap;
import java.util.List;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;

import org.xper.Dependency;
import org.xper.acq.device.AcqSamplingDevice;
import org.xper.acq.vo.ComediChannelSpec;
import org.xper.exception.ComediException;
import org.xper.time.TimeUtil;

public class ComediAnalogSamplingDevice implements AcqSamplingDevice {
	@Dependency
	TimeUtil localTimeUtil;
	@Dependency
	String deviceString;
	@Dependency
	List<ComediChannelSpec> inputChannels;
	
	ByteBuffer handle;
	ByteBuffer buf;
	DoubleBuffer dataView;
	HashMap<Integer, Integer> channelDataMap = new HashMap<Integer, Integer>();
	
	@PostConstruct
	public void init() {
		if (deviceString == null) {
			throw new ComediException("Device name is null.");
		}
		if (inputChannels == null || inputChannels.size() == 0) {
			throw new ComediException("Input channels list is null or empty.");
		}
		buf = ByteBuffer.allocateDirect(
				inputChannels.size() * Double.SIZE / 8).order(
				ByteOrder.nativeOrder());
		dataView = buf.asDoubleBuffer();
		
		handle = nCreateTask(deviceString, inputChannels.size());
		for (int i = 0; i < inputChannels.size(); i ++) {
			ComediChannelSpec spec = inputChannels.get(i);
			if (spec.getAref() == null) {
				throw new ComediException("Reference setting for channel " + spec.getChannel() + " is null."); 
			}
			nCreateChannels(handle, i, spec.getChannel(),
					spec.getMinValue(), spec.getMaxValue(), spec.getAref());
			channelDataMap.put(new Integer(spec.getChannel()), new Integer(i));
		}
	}
	
	@PreDestroy
	public void destroy () {
		nDestroy(handle);
	}

	public double getData(int channel) {
		int i = channelDataMap.get(new Integer(channel)).intValue();
		return dataView.get(i);
	}

	public long scan() {
		nScan(handle, buf);
		return localTimeUtil.currentTimeMicros();
	}
	
	native void nDestroy(ByteBuffer handle);
	native ByteBuffer nCreateTask(String deviceString, int nChannels);
	native void nCreateChannels(ByteBuffer handle, int i, short channel,
			double minValue, double maxValue, String aref);
	native void nScan (ByteBuffer handle, ByteBuffer buf);

	public TimeUtil getLocalTimeUtil() {
		return localTimeUtil;
	}

	public void setLocalTimeUtil(TimeUtil localTimeUtil) {
		this.localTimeUtil = localTimeUtil;
	}

	public String getDeviceString() {
		return deviceString;
	}

	public void setDeviceString(String deviceString) {
		this.deviceString = deviceString;
	}

	public List<ComediChannelSpec> getInputChannels() {
		return inputChannels;
	}

	public void setInputChannels(List<ComediChannelSpec> inputChannels) {
		this.inputChannels = inputChannels;
	}

}
