package org.xper.acq.mock;

import java.io.DataOutputStream;
import java.io.IOException;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.util.HashMap;
import java.util.Map;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.acq.device.AcqSamplingDevice;
import org.xper.exception.RemoteException;
import org.xper.experiment.Threadable;
import org.xper.util.ThreadHelper;

public class SocketSamplingDeviceServer implements Threadable {
	static Logger logger = Logger.getLogger(SocketSamplingDeviceServer.class);

	@Dependency
	int port = DEFAULT_SOCKET_SAMPLING_DEVICE_PORT;
	@Dependency
	int backlog = DEFAULT_BACK_LOG;
	@Dependency
	HashMap<Integer, Double> currentChannelData;
	@Dependency
	AcqSamplingDevice samplingDevice;
	@Dependency
	String host;

	public static final int DEFAULT_SOCKET_SAMPLING_DEVICE_PORT = 8890;
	private static final int DEFAULT_BACK_LOG = 10;
	ThreadHelper threadHelper = new ThreadHelper("SocketSamplingDeviceServer",
			this);
	ServerSocket server = null;

	public SocketSamplingDeviceServer(int port, int backlog) {
		this.port = port;
		this.backlog = backlog;
	}

	public SocketSamplingDeviceServer(int backlog) {
		this(DEFAULT_SOCKET_SAMPLING_DEVICE_PORT, backlog);
	}

	public SocketSamplingDeviceServer() {
		this(DEFAULT_SOCKET_SAMPLING_DEVICE_PORT, DEFAULT_BACK_LOG);
	}

	public boolean isRunning() {
		return threadHelper.isRunning();
	}

	public void start() {
		threadHelper.start();
	}

	public void stop() {
		if (isRunning()) {
			threadHelper.stop();
			try {
				server.close();
			} catch (Exception e) {
			}
			threadHelper.join();
		}
	}

	void scan() {
		samplingDevice.scan();
		for (Map.Entry<Integer, Double> ent : currentChannelData.entrySet()) {
			ent.setValue(samplingDevice.getData(ent.getKey()));
		}
	}

	/**
	 * This will stop until next request when stop method is called.
	 * @throws IOException
	 */
	private void handleRequest() throws IOException {
		Socket con = null;
		try {
			con = server.accept();
			scan();
			DataOutputStream os = new DataOutputStream(con.getOutputStream());
			int size = currentChannelData.size();
			os.writeInt(size);
			for (Map.Entry<Integer, Double> ent : currentChannelData.entrySet()) {
				os.writeInt(ent.getKey());
				os.writeDouble(ent.getValue());
			}
			os.close();
		} catch (SocketTimeoutException e) {
		} finally {
			try {
				if (con != null) {
					con.close();
				}
			} catch (Exception e) {
				logger.warn(e.getMessage());
				e.printStackTrace();
			}
		}
	}

	public void run() {
		try {
			server = new ServerSocket(port, backlog, InetAddress.getByName(host));
			System.out.println("SocketSamplingDeviceServer started on host " + host + " port " + port);
			
			threadHelper.started();
			while (!threadHelper.isDone()) {
				handleRequest();
			}
		} catch (Exception e) {
			if (!threadHelper.isDone()) {
				throw new RemoteException(e);
			}
		} finally {
			try {
				threadHelper.stopped();
			} catch (Exception e) {
				logger.warn(e.getMessage());
				e.printStackTrace();
			}
		}
	}

	public AcqSamplingDevice getSamplingDevice() {
		return samplingDevice;
	}

	public void setSamplingDevice(AcqSamplingDevice samplingDevice) {
		this.samplingDevice = samplingDevice;
	}

	public HashMap<Integer, Double> getCurrentChannelData() {
		return currentChannelData;
	}

	public void setCurrentChannelData(
			HashMap<Integer, Double> currentChannelData) {
		this.currentChannelData = currentChannelData;
	}

	public String getHost() {
		return host;
	}

	public void setHost(String host) {
		this.host = host;
	}	

}
