package org.xper.rfplot;

import java.io.DataInputStream;
import java.io.IOException;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.util.concurrent.atomic.AtomicReference;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.exception.RemoteException;
import org.xper.experiment.ExperimentTask;
import org.xper.experiment.TaskDataSource;
import org.xper.experiment.Threadable;
import org.xper.util.ThreadHelper;

public class RFPlotTaskDataSource implements TaskDataSource, Threadable {
	static Logger logger = Logger.getLogger(RFPlotTaskDataSource.class);
	
	public static final int DEFAULT_RF_PLOT_TASK_DATA_SOURCE_PORT = 8892;
	private static final int DEFAULT_BACK_LOG = 10;
	
	@Dependency
	int port = DEFAULT_RF_PLOT_TASK_DATA_SOURCE_PORT;
	@Dependency
	int backlog = DEFAULT_BACK_LOG;
	@Dependency
	String host;

	public int getBacklog() {
		return backlog;
	}

	public void setBacklog(int backlog) {
		this.backlog = backlog;
	}
	
	public static final int RFPLOT_STOP = 0;
	public static final int RFPLOT_STIM_SPEC = 1;
	public static final int RFPLOT_XFM_SPEC = 2;
	
	ServerSocket server = null;
	
	AtomicReference<ExperimentTask> currentTask = new AtomicReference<ExperimentTask>();
	ThreadHelper threadHelper = new ThreadHelper("RFPlotTaskDataSource", this);
	
	public boolean isRunning() {
		return threadHelper.isRunning();
	}
	
	public RFPlotTaskDataSource (int port, int backlog) {
		this.port = port;
		this.backlog = backlog;
	}
	public RFPlotTaskDataSource (int backlog) {
		this(DEFAULT_RF_PLOT_TASK_DATA_SOURCE_PORT, backlog);
	}
	
	public RFPlotTaskDataSource () {
		this(DEFAULT_RF_PLOT_TASK_DATA_SOURCE_PORT, DEFAULT_BACK_LOG);
	}

	public ExperimentTask getNextTask() {
		ExperimentTask task = currentTask.get();
		if (task == null || task.getStimSpec() == null || task.getXfmSpec() == null) return null;
		else return task;
	}

	public void ungetTask(ExperimentTask t) {
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
	
	private void handleRequest() throws IOException {
		Socket con = null;
		try {
			con = server.accept();
			DataInputStream input = new DataInputStream(con.getInputStream());
			int response = input.readInt();
			if (response != RFPLOT_STOP) {
				String spec = input.readUTF();
							
				ExperimentTask task = currentTask.get();
				if (task == null) task = new ExperimentTask();
				
				switch (response) {
				case RFPLOT_STIM_SPEC: 
					task.setStimSpec(spec);
					break;
				case RFPLOT_XFM_SPEC:
					task.setXfmSpec(spec);
					break;
				}
				currentTask.set(task);
			}
			input.close();
			
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
			System.out.println("RFPlotTaskDataSource started on host " + host + " port " + port);
			
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
