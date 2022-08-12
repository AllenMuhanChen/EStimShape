package org.xper.acq.comedi;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.List;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;

import org.xper.Dependency;
import org.xper.acq.device.AcqStreamingDevice;
import org.xper.acq.vo.ComediChannelSpec;
import org.xper.exception.ComediException;

public class ComediAnalogStreamingDevice implements AcqStreamingDevice {
	@Dependency
	List<ComediChannelSpec> inputChannels;
	@Dependency
	double masterFreqency;
	@Dependency
	int bufferSize;
	@Dependency
	String deviceString;
	
	public static int MIN_BUFFER_SIZE = 10000;

	ByteBuffer handle;
	ByteBuffer buf;
	
	public void connect() {
	}

	public void disconnect() {
	}

	@PostConstruct
	public void init() {
		if (deviceString == null) {
			throw new ComediException("Device name is null.");
		}
		if (inputChannels == null || inputChannels.size() == 0) {
			throw new ComediException("Input channels list is null or empty.");
		}
		// bufferSize is number of samples.
		buf = ByteBuffer.allocateDirect(bufferSize * Double.SIZE / 8).order(
				ByteOrder.nativeOrder());

		handle = nCreateTask(deviceString, inputChannels.size(), masterFreqency, bufferSize);
		for (int i = 0; i < inputChannels.size(); i ++) {
			ComediChannelSpec spec = inputChannels.get(i);
			if (spec.getAref() == null) {
				throw new ComediException("Reference setting for channel " + spec.getChannel() + " is null."); 
			}
			nCreateChannels(handle, i, spec.getChannel(),
					spec.getMinValue(), spec.getMaxValue(), spec.getAref());
		}
		nConfigTask(handle);
	}

	@PreDestroy
	public void destroy() {
		nDestroy(handle);
	}

	public void start() {
		nStart(handle);
	}

	public void stop() {
		nStop(handle);
	}

	public double[] scan() {
		// n is number of samples.
		int n = nScan(handle, buf);
		if (n == 0)
			return null;

		double[] ret = new double[n];
		buf.asDoubleBuffer().get(ret);
		return ret;
	}

	native void nStart(ByteBuffer handle);

	native void nStop(ByteBuffer handle);

	native ByteBuffer nCreateTask(String deviceString, int nChannels, double masterFreq, int bufferSize);

	native void nDestroy(ByteBuffer handle);

	native void nCreateChannels(ByteBuffer handle, int i, short channel,
			double minValue, double maxValue, String aref);

	native void nConfigTask(ByteBuffer handle);

	native int nScan(ByteBuffer handle, ByteBuffer buf);

	public List<ComediChannelSpec> getInputChannels() {
		return inputChannels;
	}

	public void setInputChannels(List<ComediChannelSpec> inputChannels) {
		this.inputChannels = inputChannels;
	}

	public int getBufferSize() {
		return bufferSize;
	}

	public void setBufferSize(int bufferSize) {
		if (bufferSize < MIN_BUFFER_SIZE) {
			this.bufferSize = MIN_BUFFER_SIZE;
		} else {
			this.bufferSize = bufferSize;
		}
	}

	public double getMasterFreqency() {
		return masterFreqency;
	}

	public void setMasterFreqency(double masterFreqency) {
		this.masterFreqency = masterFreqency;
	}

	public String getDeviceString() {
		return deviceString;
	}

	public void setDeviceString(String deviceString) {
		this.deviceString = deviceString;
	}
}
