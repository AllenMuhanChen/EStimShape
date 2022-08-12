package org.xper.rds;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.net.Socket;

import org.apache.log4j.Logger;
import org.xper.Dependency;

public class RdsControlClient {
	static Logger logger = Logger.getLogger(RdsControlClient.class);
	
	/**
	 * Dependencies. Should not change after deployment.
	 */
	@Dependency
	String host;
	@Dependency
	int port = RdsControlServer.DEFAULT_RDS_CONTROL_SEVER;

	public RdsControlClient(String host, int port) {
		this.host = host;
		this.port = port;
	}

	public RdsControlClient(String host) {
		this.host = host;
	}

	public void stop() {
		System.out.println("Stop RdsControlServer.");
		doCommand(RdsControlServer.STOP);
	}

	public void setColor(float r, float g, float b) {
		doCommand(RdsControlServer.COLOR, r, g, b);
	}

	public void setCoordinate(float x, float y) {
		doCommand(RdsControlServer.COORDINATE, x, y);
	}
	
	public void setSize(float value) {
		doCommand(RdsControlServer.SIZE, value);
	}

	void doCommand(int command, float ... values) {
		Socket client;
		try {
			client = new Socket(host, port);
			DataOutputStream os = new DataOutputStream(client.getOutputStream());
			os.writeInt(command);
			for (float v : values) {
				os.writeFloat(v);
			}
			if (command != RdsControlServer.STOP) {
				DataInputStream is = new DataInputStream(client.getInputStream());
				is.readInt();
			}
			client.close();
		} catch (Exception e) {
			//throw new RemoteException(e);
			logger.warn("Connect to RdsControlServer failed.");
		}
	}
}
