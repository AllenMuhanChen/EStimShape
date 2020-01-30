package org.xper.acq.ni;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.List;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;

import org.xper.Dependency;
import org.xper.acq.device.DigitalPortOutDevice;
import org.xper.exception.NiException;

public class NiDigitalPortOutDevice implements DigitalPortOutDevice {
	@Dependency
	List<Integer> ports;
	@Dependency
	String deviceString;
	
	ByteBuffer handle;
	ByteBuffer buf;
	
	@PostConstruct
	public void init () {
		if (deviceString == null) {
			throw new NiException("Device name is null.");
		}
		if (ports == null || ports.size() == 0) {
			throw new NiException("Output ports list is null or empty.");
		}
		buf = ByteBuffer.allocateDirect(
				ports.size() * Long.SIZE / 8).order(
				ByteOrder.nativeOrder());
		handle = nCreateTask(ports.size());
		for (Integer port : ports) {
			nCreateChannels(handle, deviceString + "/port" + port);
		}
	}
	
	@PreDestroy
	public void destroy () {
		nDestroy(handle);
	}
	
	public void write (long [] data) {
		if (data.length != ports.size()) {
			throw new NiException("Data length incorrect, expecting " + ports.size() + " find " + data.length);
		}
		for (int i = 0; i < data.length; i ++) {
			buf.putLong(data[i]);
		}
		buf.flip();
		
		nWrite(handle, buf);
	}
	
	native ByteBuffer nCreateTask(int nChannels);
	native void nDestroy(ByteBuffer handle);
	native void nCreateChannels (ByteBuffer handle, String channel);
	native void nWrite (ByteBuffer handle, ByteBuffer data);

	public List<Integer> getPorts() {
		return ports;
	}

	public void setPorts(List<Integer> ports) {
		this.ports = ports;
	}

	public String getDeviceString() {
		return deviceString;
	}

	public void setDeviceString(String deviceString) {
		this.deviceString = deviceString;
	}
}
