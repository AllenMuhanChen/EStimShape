package org.xper.acq.comedi;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.List;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;

import org.xper.Dependency;
import org.xper.acq.device.DigitalPortOutDevice;
import org.xper.exception.ComediException;

public class ComediDigitalPortOutDevice implements DigitalPortOutDevice {
	/**
	 * Each port consists of 8 digital lines by default (It can be changed using the linesPerPort property). 
	 * Port number starts from 0.
	 */
	@Dependency
	List<Integer> ports;
	/**
	 * Comedi driver string. e.g "/dev/comedi0".
	 */
	@Dependency
	String deviceString;
	@Dependency
	int linesPerPort = 8;

	ByteBuffer handle;
	ByteBuffer dataBuf;
	
	@PostConstruct
	public void init () {
		if (deviceString == null) {
			throw new ComediException("Device name is null.");
		}
		if (ports == null || ports.size() == 0) {
			throw new ComediException("Output ports list is null or empty.");
		}
		dataBuf = ByteBuffer.allocateDirect(
				ports.size() * Long.SIZE / 8).order(
				ByteOrder.nativeOrder());
		
		ByteBuffer portBuf = ByteBuffer.allocateDirect(
				ports.size() * Integer.SIZE / 8).order(
						ByteOrder.nativeOrder());
		for (int i = 0; i < ports.size(); i ++) {
			portBuf.putInt(ports.get(i));
		}
		portBuf.flip();
		handle = nCreateTask(deviceString, portBuf, linesPerPort);
	}
	
	@PreDestroy
	public void destroy () {
		nDestroy(handle);
	}
	
	public void write (long [] data) {
		if (data.length != ports.size()) {
			throw new ComediException("Data length incorrect, expecting " + ports.size() + " find " + data.length);
		}
		for (int i = 0; i < data.length; i ++) {
			dataBuf.putLong(data[i]);
		}
		dataBuf.flip();
		
		nWrite(handle, dataBuf);
	}
	
	native ByteBuffer nCreateTask(String deviceString, ByteBuffer ports, int linesPerPort);
	native void nDestroy(ByteBuffer handle);
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
	
	public int getLinesPerPort() {
		return linesPerPort;
	}

	public void setLinesPerPort(int linesPerPort) {
		this.linesPerPort = linesPerPort;
	}
}
