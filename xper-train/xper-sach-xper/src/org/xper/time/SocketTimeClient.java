package org.xper.time;

import java.io.DataInputStream;
import java.net.Socket;

import org.xper.Dependency;
import org.xper.exception.RemoteException;

/**
 * Thread safe. Define one for each combination of host and port.
 * 
 * @author Zhihong Wang
 * 
 */
public class SocketTimeClient implements TimeUtil {
	@Dependency
	String host;
	@Dependency
	int port = SocketTimeServer.DEFAULT_TIME_PORT;

	public SocketTimeClient(String host, int port) {
		this.host = host;
		this.port = port;
	}

	public SocketTimeClient(String host) {
		this.host = host;
	}

	public long currentTimeMicros() {
		Socket client;
		long time;
		try {
			client = new Socket(host, port);
			DataInputStream input = new DataInputStream(client.getInputStream());
			time = input.readLong();
			input.close();
			client.close();
		} catch (Exception e) {
			throw new RemoteException(e);
		}

		return time;
	}
}
