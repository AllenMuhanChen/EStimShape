package org.xper.acq.ni;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.List;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;

import org.xper.Dependency;
import org.xper.acq.device.AcqStreamingDevice;
import org.xper.acq.vo.NiChannelSpec;
import org.xper.exception.NiException;

public class NiAnalogStreamingDevice implements AcqStreamingDevice {
	@Dependency
	List<NiChannelSpec> inputChannels;
	@Dependency
	double masterFreqency;
	@Dependency
	int bufferSize;
	@Dependency
	String deviceString;
	
	public static int MIN_BUFFER_SIZE = 10000;

	ByteBuffer handle;
	ByteBuffer buf;

	@PostConstruct
	public void init() {
		if (deviceString == null) {
			throw new NiException("Device name is null.");
		}
		if (inputChannels == null || inputChannels.size() == 0) {
			throw new NiException("Input channels list is null or empty.");
		}
		// bufferSize is samples per Channel.
		buf = ByteBuffer.allocateDirect(bufferSize * Double.SIZE / 8 * inputChannels.size()).order(
				ByteOrder.nativeOrder());

		handle = nCreateTask(inputChannels.size());
		for (NiChannelSpec spec : inputChannels) {
			// Using channel default reference setting.
			nCreateChannels(handle, deviceString + "/ai" + spec.getChannel(),
					spec.getMinValue(), spec.getMaxValue());
		}
		nConfigTask(handle, masterFreqency, bufferSize);
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

	/**
	 * Scan all channels once, return the data as one double per channel.
	 */
	public double[] scan() {
		// n is samples per channel.
		int n = nScan(handle, buf);
		if (n == 0)
			return null;

		double[] ret = new double[n * inputChannels.size()];
		buf.asDoubleBuffer().get(ret);
		return ret;
	}

	native void nStart(ByteBuffer handle);

	native void nStop(ByteBuffer handle);

	native ByteBuffer nCreateTask(int nChannels);

	native void nDestroy(ByteBuffer handle);

	native void nCreateChannels(ByteBuffer handle, String channel,
			double minValue, double MaxValue);

	native void nConfigTask(ByteBuffer handle, double samplingRate, long bufSize);

	native int nScan(ByteBuffer handle, ByteBuffer buf);

	public List<NiChannelSpec> getInputChannels() {
		return inputChannels;
	}

	public void setInputChannels(List<NiChannelSpec> inputChannels) {
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

	public void connect() {
	}

	public void disconnect() {
	}
}
