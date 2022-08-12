package org.xper.experiment;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.net.Socket;

import org.apache.log4j.Logger;
import org.xper.Dependency;

public class ExperimentRunnerClient {
	static Logger logger = Logger.getLogger(ExperimentRunnerClient.class);
	
	/**
	 * Dependencies. Should not change after deployment.
	 */
	@Dependency
	String host;
	@Dependency
	int port = ExperimentRunner.DEFAULT_XPER_PORT;

	public ExperimentRunnerClient(String host, int port) {
		this.host = host;
		this.port = port;
	}

	public ExperimentRunnerClient(String host) {
		this.host = host;
	}

	public void stop() {
		System.out.println("Stop experiment.");
		doCommand(ExperimentRunner.STOP);
	}

	public void pause() {
		System.out.println("Pause experiment.");
		doCommand(ExperimentRunner.PAUSE);
	}

	public void resume() {
		System.out.println("Resume experiment.");
		doCommand(ExperimentRunner.RESUME);
	}

	void doCommand(int command) {
		Socket client;
		try {
			client = new Socket(host, port);
			DataOutputStream os = new DataOutputStream(client.getOutputStream());
			os.writeInt(command);
			DataInputStream is = new DataInputStream(client.getInputStream());
			is.readInt();
			client.close();
		} catch (Exception e) {
			//throw new RemoteException(e);
			logger.warn("Connect to ExperimentRunner failed. Experiment may not be running.");
		}
	}
}
