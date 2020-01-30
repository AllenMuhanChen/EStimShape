package org.xper.acq.mock;

import java.io.DataInputStream;
import java.net.Socket;
import java.util.HashMap;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.acq.device.AcqSamplingDevice;
import org.xper.time.TimeUtil;


public class SocketSamplingDeviceClient implements AcqSamplingDevice {
	static Logger logger = Logger.getLogger(SocketSamplingDeviceClient.class);
	
	@Dependency
	String host;
	@Dependency
	int port = SocketSamplingDeviceServer.DEFAULT_SOCKET_SAMPLING_DEVICE_PORT;
	@Dependency
	TimeUtil localTimeUtil;
	
	HashMap<Integer, Double> currentChannelData = new HashMap<Integer, Double>();
	
	public SocketSamplingDeviceClient(String host, int port) {
		this.host = host;
		this.port = port;
	}

	public SocketSamplingDeviceClient(String host) {
		this.host = host;
	}

	public double getData(int channel) {
		if (currentChannelData.containsKey(channel)) {
			return currentChannelData.get(channel);
		} else {
			return 0;
		}
	}

	public long scan() {
		Socket client;
		try {
			client = new Socket(host, port);
			if (logger.isDebugEnabled()) {
				logger.debug("SocketSamplingDeviceClient connecting to " + host + " port " + port);
			}
			DataInputStream input = new DataInputStream(client.getInputStream());
			int n = input.readInt();
			for (int i = 0; i < n; i ++) {
				int chan = input.readInt();
				double volt = input.readDouble();
				currentChannelData.put(chan, volt);
			}
			input.close();
			client.close();
		} catch (Exception e) {
			//throw new RemoteException(e);
		}
		// Use local timestamp because socket sampling server might have different time
		return localTimeUtil.currentTimeMicros();
	}

	public TimeUtil getLocalTimeUtil() {
		return localTimeUtil;
	}

	public void setLocalTimeUtil(TimeUtil localTimeUtil) {
		this.localTimeUtil = localTimeUtil;
	}

}
