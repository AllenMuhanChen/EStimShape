package org.xper.acq;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.exception.RemoteException;
import org.xper.time.TimeServer;

public class SocketDataAcqServer {
	static Logger logger = Logger.getLogger(SocketDataAcqServer.class);
	
	@Dependency 
	AcqDeviceController acqDeviceController;
	@Dependency
	TimeServer timeServer;
	@Dependency
	int port = DEFAULT_ACQ_PORT;
	@Dependency
	int backlog = DEFAULT_BACK_LOG;
	@Dependency
	String host;

	public static final int DEFAULT_ACQ_PORT = 8891;
	private static final int DEFAULT_BACK_LOG = 10;

	/**
	 * Commands.
	 */
	public static final int CONNECT = 1;
	public static final int DISCONNECT = 2;
	public static final int START = 3;
	public static final int STOP = 4;
	public static final int SHUTDOWN = 5;

	ServerSocket server = null;

	boolean done = false;

	public SocketDataAcqServer(int port, int backlog) {
		this.port = port;
		this.backlog = backlog;
	}

	public SocketDataAcqServer(int backlog) {
		this.backlog = backlog;
	}

	public SocketDataAcqServer() {
	}

	void handleCommand() throws IOException {
		Socket con = server.accept();
		try {
			DataInputStream is = new DataInputStream(con.getInputStream());
			int command = is.readInt();
			switch (command) {
			case CONNECT:
				acqDeviceController.connect();
				break;
			case DISCONNECT:
				acqDeviceController.disconnect();
				break;
			case START:
				acqDeviceController.start();
				break;
			case STOP:
				acqDeviceController.stop();
				break;
			case SHUTDOWN:
				timeServer.stop();
				done = true;
				break;
			}
			if (command != SHUTDOWN) {
				DataOutputStream os = new DataOutputStream(con
						.getOutputStream());
				os.writeInt(0);
			}
		} finally {
			try {
				con.close();
			} catch (Exception e) {
				logger.warn(e.getMessage());
				e.printStackTrace();
			}
		}
	}

	protected void listen() {
		try {
			server = new ServerSocket(port, backlog, InetAddress.getByName(host));
			System.out.println("SocketDataAcqServer started on host " + host + " port " + port);
			
			while (!done) {
				handleCommand();
			}
		} catch (Exception e) {
			throw new RemoteException(e);
		} finally {
			try {
				server.close();
			} catch (Exception e) {
				logger.warn(e.getMessage());
				e.printStackTrace();
			}
		}
	}

	public void run() {
		done = false;
		timeServer.start();
		listen();
	}
	
	public void shutdown() {
		if (!server.isClosed()) {
			SocketDataAcqClient client = new SocketDataAcqClient("localhost", port);
			client.shutdown();
		}
	}

	public AcqDeviceController getAcqDeviceController() {
		return acqDeviceController;
	}

	public void setAcqDeviceController(AcqDeviceController acqDeviceController) {
		this.acqDeviceController = acqDeviceController;
	}

	public int getPort() {
		return port;
	}

	public void setPort(int port) {
		this.port = port;
	}

	public int getBacklog() {
		return backlog;
	}

	public void setBacklog(int backlog) {
		this.backlog = backlog;
	}

	public TimeServer getTimeServer() {
		return timeServer;
	}

	public void setTimeServer(TimeServer timeServer) {
		this.timeServer = timeServer;
	}

	public String getHost() {
		return host;
	}

	public void setHost(String host) {
		this.host = host;
	}
	
	
}
