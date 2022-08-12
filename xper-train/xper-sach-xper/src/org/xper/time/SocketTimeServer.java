package org.xper.time;

import java.io.DataOutputStream;
import java.io.IOException;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketTimeoutException;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.exception.RemoteException;
import org.xper.util.ThreadHelper;

/**
 * Only one exists for the entire system. Deploy as singleton.
 * 
 * @author Zhihong Wang
 * 
 */

public class SocketTimeServer implements TimeServer {
	static Logger logger = Logger.getLogger(SocketTimeServer.class);

	public static final int DEFAULT_TIME_PORT = 8888;
	private static final int DEFAULT_BACK_LOG = 10;

	@Dependency
	TimeUtil localTimeUtil;
	@Dependency
	int port = DEFAULT_TIME_PORT;
	@Dependency
	int backlog = DEFAULT_BACK_LOG;
	@Dependency
	String host;

	long prior = 0;
	ServerSocket server = null;
	ThreadHelper threadHelper = new ThreadHelper("TimeServer", this);

	public SocketTimeServer(int port, int backlog) {
		this.port = port;
		this.backlog = backlog;
	}

	public SocketTimeServer(int backlog) {
		this(DEFAULT_TIME_PORT, backlog);
	}

	public SocketTimeServer() {
		this(DEFAULT_TIME_PORT, DEFAULT_BACK_LOG);
	}

	/**
	 * When stop method is called, accept in this method will be still waiting until the next request comes.
	 * Then after handling the next request, the server stops.
	 * @throws IOException
	 */
	synchronized private void handleRequest() throws IOException {
		Socket con = null;
		try {
			con = server.accept();
			DataOutputStream os = new DataOutputStream(con.getOutputStream());
			long current = localTimeUtil.currentTimeMicros();
			if (logger.isDebugEnabled()) {
				logger.debug(" current timestamp: " + current
						+ "; prior timestamp: " + prior);
			}
			if (current < prior) {
				throw new RemoteException(
						"Time Server timestamp order inverted.");
			}
			prior = current;
			os.writeLong(current);
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

	public void start() {
		threadHelper.start();
	}

	public int getPort() {
		return port;
	}

	public void setPort(int port) {
		this.port = port;
	}

	public TimeUtil getLocalTimeUtil() {
		return localTimeUtil;
	}

	public void setLocalTimeUtil(TimeUtil localTimeUtil) {
		this.localTimeUtil = localTimeUtil;
	}

	public boolean isRunning() {
		return threadHelper.isRunning();
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

	public void run() {
		try {
			server = new ServerSocket(port, backlog, InetAddress.getByName(host));
			System.out.println("SocketTimeServer started on host " + host + " port " + port);

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

	public String getHost() {
		return host;
	}

	public void setHost(String host) {
		this.host = host;
	}
	
	
}
