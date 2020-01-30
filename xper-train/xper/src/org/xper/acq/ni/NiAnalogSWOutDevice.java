package org.xper.acq.ni;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.List;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;

import org.xper.Dependency;
import org.xper.acq.device.AnalogOutDevice;
import org.xper.acq.vo.NiChannelSpec;
import org.xper.exception.NiException;

/**
 * Software timing analog output.
 * 
 * @author John
 *
 */
public class NiAnalogSWOutDevice implements AnalogOutDevice {
	@Dependency
	List<NiChannelSpec> outputChannels;
	@Dependency
	String deviceString;
	
	ByteBuffer handle;
	ByteBuffer buf;
	
	@PostConstruct
	public void init () {
		if (deviceString == null) {
			throw new NiException("Device name is null.");
		}
		if (outputChannels == null || outputChannels.size() == 0) {
			throw new NiException("Output channels list is null or empty.");
		}
		buf = ByteBuffer.allocateDirect(
				outputChannels.size() * Double.SIZE / 8).order(
				ByteOrder.nativeOrder());
		handle = nCreateTask(outputChannels.size());
		for (NiChannelSpec spec : outputChannels) {
			nCreateChannels(handle, deviceString + "/ao" + spec.getChannel(), spec.getMinValue(), spec.getMaxValue());
		}
	}
	
	@PreDestroy
	public void destroy () {
		nDestroy(handle);
	}
		
	public void write (double[] data) {
		if (data.length != outputChannels.size()) {
			throw new NiException("Data length incorrect, expecting " + outputChannels.size() + " find " + data.length);
		}
		for (int i = 0; i < outputChannels.size(); i ++) {
			buf.putDouble(data[i]);
		}
			
		buf.flip();
		
		nWrite(handle, buf);
	}
	
	native ByteBuffer nCreateTask (int nChannels);
	native void nDestroy(ByteBuffer handle);
	native void nCreateChannels (ByteBuffer handle, String channel, double minValue, double MaxValue);
	native void nWrite (ByteBuffer handle, ByteBuffer data);

	public List<NiChannelSpec> getOutputChannels() {
		return outputChannels;
	}

	public void setOutputChannels(List<NiChannelSpec> outputChannels) {
		this.outputChannels = outputChannels;
	}

	public String getDeviceString() {
		return deviceString;
	}

	public void setDeviceString(String deviceString) {
		this.deviceString = deviceString;
	}
}
