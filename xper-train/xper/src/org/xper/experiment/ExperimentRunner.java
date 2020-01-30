package org.xper.experiment;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.exception.RemoteException;

public class ExperimentRunner {
	static Logger logger = Logger.getLogger(ExperimentRunner.class);
	
	@Dependency
	Experiment experiment;
	@Dependency
	int port = DEFAULT_XPER_PORT;
	@Dependency
	int backlog = DEFAULT_BACK_LOG;
	@Dependency
	String host;

	public static final int DEFAULT_XPER_PORT = 8889;

	/**
	 * Commands.
	 */
	public static final int PAUSE = 1;
	public static final int RESUME = 2;
	public static final int STOP = 3;
	private static final int DEFAULT_BACK_LOG = 10;
	
	ServerSocket server = null;
	boolean done = false;

	public ExperimentRunner(int port, int backlog) {
		this.port = port;
		this.backlog = backlog;
	}

	public ExperimentRunner(int backlog) {
		this.backlog = backlog;
	}

	public ExperimentRunner() {
	}

	public Experiment getExperiment() {
		return experiment;
	}

	public void setExperiment(Experiment experiment) {
		this.experiment = experiment;
	}

	void handleCommand() throws IOException {
		Socket con = server.accept();
		try {
			DataInputStream is = new DataInputStream(con.getInputStream());
			int command = is.readInt();
			switch (command) {
			case PAUSE:
				experiment.setPause(true);
				break;
			case RESUME:
				experiment.setPause(false);
				break;
			case STOP:
				experiment.stop();
				done = true;
				break;
			}
			DataOutputStream os = new DataOutputStream(con.getOutputStream());
			os.writeInt(0);
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
			System.out.println("ExperimentRunner started on host " + host + " port " + port);
			while (!done) {
				handleCommand();
			}
		} catch (Exception e) {
			if (experiment.isRunning()) {
				experiment.stop();
			}
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
		experiment.start();
		listen();
	}

	public void stop() {
		if (experiment.isRunning()) {
			experiment.stop();
		}
	}

	public String getHost() {
		return host;
	}

	public void setHost(String host) {
		this.host = host;
	}
	
	
}
