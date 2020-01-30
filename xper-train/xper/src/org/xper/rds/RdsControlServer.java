package org.xper.rds;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketTimeoutException;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.exception.RemoteException;
import org.xper.experiment.Threadable;
import org.xper.eye.EyeMonitor;
import org.xper.util.ThreadHelper;

public class RdsControlServer implements Threadable {
	static Logger logger = Logger.getLogger(RdsControlServer.class);
	
	@Dependency
	int port = DEFAULT_RDS_CONTROL_SEVER;
	@Dependency
	int backlog = DEFAULT_BACK_LOG;
	@Dependency
	String host;

	@Dependency
	RdsFixationPoint rdsFixationPoint;
	@Dependency
	EyeMonitor eyeMonitor;
	
	public static final int DEFAULT_RDS_CONTROL_SEVER = 8887;

	/**
	 * Commands.
	 */
	public static final int STOP = 0;
	public static final int SIZE = 1;
	public static final int COLOR = 2;
	public static final int COORDINATE = 3;
	
	private static final int DEFAULT_BACK_LOG = 10;
	
	ServerSocket server = null;
	ThreadHelper threadHelper = new ThreadHelper("RdsControlServer", this);

	public RdsControlServer(int port, int backlog) {
		this.port = port;
		this.backlog = backlog;
	}

	public RdsControlServer(int backlog) {
		this.backlog = backlog;
	}

	public RdsControlServer() {
	}

	void handleRequest() throws IOException {
		Socket con = null;
		try {
			con = server.accept();
			DataInputStream is = new DataInputStream(con.getInputStream());
			int command = is.readInt();
			switch (command) {
			case SIZE:
				setSize(is.readFloat());
				break;
			case COORDINATE:
				setCoordinate(is.readFloat(), is.readFloat());
				break;
			case COLOR:
				setColor(is.readFloat(), is.readFloat(), is.readFloat());
				break;
			case STOP:
				stop();
				break;
			}
			if (command != STOP) {
				DataOutputStream os = new DataOutputStream(con.getOutputStream());
				os.writeInt(0);
			}
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

	private void setColor(float r, float g, float b) {
		rdsFixationPoint.setFixationColor(new RGBColor(r, g, b));
	}

	private void setCoordinate(float x, float y) {
		rdsFixationPoint.setFixationPosition(new Coordinates2D(x, y));
		eyeMonitor.setEyeWinCenter(new Coordinates2D(x, y));
	}

	private void setSize(float value) {
		rdsFixationPoint.setFixationSize(value);
	}

	public void run() {
		try {
			server = new ServerSocket(port, backlog, InetAddress.getByName(host));
			System.out.println("RdsControlServer started on host " + host + " port " + port);
			
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

	@Override
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
			// only join if called outside message handling method.
			// when called within message handling method, join will deadlock.
			//threadHelper.join();
		}
	}

	public RdsFixationPoint getRdsFixationPoint() {
		return rdsFixationPoint;
	}

	public void setRdsFixationPoint(RdsFixationPoint rdsFixationPoint) {
		this.rdsFixationPoint = rdsFixationPoint;
	}

	public EyeMonitor getEyeMonitor() {
		return eyeMonitor;
	}

	public void setEyeMonitor(EyeMonitor eyeMonitor) {
		this.eyeMonitor = eyeMonitor;
	}
}
