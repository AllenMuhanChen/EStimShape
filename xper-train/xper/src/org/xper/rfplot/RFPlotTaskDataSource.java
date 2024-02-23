package org.xper.rfplot;

import java.io.DataInputStream;
import java.io.IOException;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;
import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.exception.RemoteException;
import org.xper.experiment.ExperimentTask;
import org.xper.experiment.TaskDataSource;
import org.xper.experiment.Threadable;
import org.xper.rfplot.drawing.RFPlotDrawable;
import org.xper.time.TimeUtil;
import org.xper.util.DbUtil;
import org.xper.util.ThreadHelper;

import javax.sql.DataSource;

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
	@Dependency
	Map<String, RFPlotDrawable> refObjMap;
	@Dependency
	TimeUtil timeUtil;
	@Dependency
	DbUtil dbUtil;

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

	@Override
	public ExperimentTask getNextTask() {
		ExperimentTask task = currentTask.get();
		if (task == null){
			task = new ExperimentTask();
		}
		task.setTaskId(timeUtil.currentTimeMicros());
		task.setGenId(-1);
		task.setStimId(task.getTaskId());
		if (task.getStimSpec() == null) {
			RFPlotDrawable firstStimObj = getFirstStimObj();
			task.setStimSpec(RFPlotStimSpec.getStimSpecFromRFPlotDrawable(firstStimObj));
		}
		if (task.getXfmSpec() == null){
			task.setXfmSpec(RFPlotXfmSpec.fromXml(null).toXml());
		}

		currentTask.set(task);
		return currentTask.get();

	}

	private RFPlotDrawable getFirstStimObj() {
		return (RFPlotDrawable) refObjMap.values().toArray()[0];
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

	/**
	 * When a request for a new StimSpec or XfmSpec is received, the server
	 * will update the current task with the new spec(s). Since the task is an object,
	 * the changes will apply even in the middle of a task.
	 *
	 */
	private void handleRequest() throws IOException {
		Socket con = null;
		try {
			con = server.accept();
			DataInputStream input = new DataInputStream(con.getInputStream());
			int response = input.readInt();

			if (response != RFPLOT_STOP) {
				long currentTimeMicros = timeUtil.currentTimeMicros();
				String spec = input.readUTF();

				ExperimentTask task = currentTask.get();
				if (task == null) {
					task = new ExperimentTask();
				}
				task.setTaskId(currentTimeMicros);
				switch (response) {
					case RFPLOT_STIM_SPEC:
						task.setStimSpec(spec);
						task.setStimId(currentTimeMicros);
						// Write the part of stim spec actually relevant for drawing into database
						RFPlotStimSpec rfPlotStimSpec = RFPlotStimSpec.fromXml(spec);
						dbUtil.writeStimSpec(currentTimeMicros, rfPlotStimSpec.getStimSpec());
						break;
					case RFPLOT_XFM_SPEC:
						task.setXfmSpec(spec);
						task.setXfmId(currentTimeMicros);
						dbUtil.writeXfmSpec(currentTimeMicros, spec);
						break;
				}
				currentTask.set(task);
				insertTask(task.getTaskId(), task.getStimId(), task.getXfmId());
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

	/**
	 * Inserts a new task into the RFPlotTasks table.
	 *
	 * @param taskId the ID of the task
	 * @param stimId the stimulus ID
	 * @param xfmId the transformation ID
	 */
	public void insertTask(long taskId, long stimId, long xfmId) {
		// SQL statement to insert a new task
		String sql = "INSERT INTO RFPlotTasks (task_id, stim_id, xfm_id) VALUES (?, ?, ?)";

		try (Connection conn = dbUtil.getDataSource().getConnection();
			 PreparedStatement pstmt = conn.prepareStatement(sql)) {

			// Set parameters for the prepared statement
			pstmt.setLong(1, taskId);
			pstmt.setLong(2, stimId);
			pstmt.setLong(3, xfmId);

			// Execute the insert operation
			pstmt.executeUpdate();

		} catch (SQLException e) {
			e.printStackTrace();
		}
	}

	public String getHost() {
		return host;
	}

	public void setHost(String host) {
		this.host = host;
	}

	public Map<String, RFPlotDrawable> getRefObjMap() {
		return refObjMap;
	}

	public void setRefObjMap(Map<String, RFPlotDrawable> refObjMap) {
		this.refObjMap = refObjMap;
	}

	public TimeUtil getTimeUtil() {
		return timeUtil;
	}

	public void setTimeUtil(TimeUtil timeUtil) {
		this.timeUtil = timeUtil;
	}

	public DbUtil getDbUtil() {
		return dbUtil;
	}

	public void setDbUtil(DbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}
}