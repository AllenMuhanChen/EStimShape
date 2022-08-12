package org.xper.acq;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.net.Socket;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.exception.RemoteException;

public class SocketDataAcqClient implements AcqDeviceController {
	static Logger logger = Logger.getLogger(SocketDataAcqClient.class);

	@Dependency
	String host;
	@Dependency
	int port = SocketDataAcqServer.DEFAULT_ACQ_PORT;

	boolean isRunning = false;

	public SocketDataAcqClient(String host, int port) {
		this.host = host;
		this.port = port;
	}

	public SocketDataAcqClient(String host) {
		this.host = host;
	}

	void doCommand(int command) {
		Socket client;
		try {
			client = new Socket(host, port);
			DataOutputStream os = new DataOutputStream(client.getOutputStream());
			os.writeInt(command);
			if (command != SocketDataAcqServer.SHUTDOWN) {
				DataInputStream is = new DataInputStream(client
						.getInputStream());
				is.readInt();
			}
			client.close();
		} catch (Exception e) {
			throw new RemoteException(e);
		}
	}

	public void connect() {
		doCommand(SocketDataAcqServer.CONNECT);
	}

	public void disconnect() {
		doCommand(SocketDataAcqServer.DISCONNECT);
	}

	public boolean isRunning() {
		return isRunning;
	}

	public void start() {
		doCommand(SocketDataAcqServer.START);
		isRunning = true;
	}

	public void stop() {
		doCommand(SocketDataAcqServer.STOP);
		isRunning = false;
	}

	public void shutdown() {
		logger.info("Shutdown acq server.");
		doCommand(SocketDataAcqServer.SHUTDOWN);
	}
}
