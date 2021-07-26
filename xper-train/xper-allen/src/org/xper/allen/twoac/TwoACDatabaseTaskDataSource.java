package org.xper.allen.twoac;

import java.util.LinkedList;
import java.util.NoSuchElementException;
import java.util.concurrent.atomic.AtomicReference;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.allen.util.AllenDbUtil;
import org.xper.db.vo.GenerationInfo;
import org.xper.experiment.DatabaseTaskDataSource;
import org.xper.experiment.ExperimentTask;
import org.xper.util.DbUtil;
import org.xper.util.ThreadHelper;

public class TwoACDatabaseTaskDataSource extends DatabaseTaskDataSource {
	static Logger logger = Logger.getLogger(DatabaseTaskDataSource.class);

	static final int DEFAULT_QUERY_INTERVAL = 1000;

	@Dependency
	AllenDbUtil dbUtil;
	@Dependency
	long queryInterval = DEFAULT_QUERY_INTERVAL;
	@Dependency
	UngetPolicy ungetBehavior;

	AtomicReference<LinkedList<TwoACExperimentTask>> currentGeneration = new AtomicReference<LinkedList<TwoACExperimentTask>>();
	ThreadHelper threadHelper = new ThreadHelper("DatabaseTaskDataSource", this);
	long currentGenId = -1;
	long lastDoneTaskId = -1;

	public boolean isRunning() {
		return threadHelper.isRunning();
	}

	public TwoACExperimentTask getNextTask() {
		try {
			LinkedList<TwoACExperimentTask> tasks = currentGeneration.get();
			if (tasks == null) {
				return null;
			}
			TwoACExperimentTask task = tasks.removeFirst();
			if (logger.isDebugEnabled()) {
				logger.debug("	Get -- Generation: " + task.getGenId() + " task: "
						+ task.getTaskId());
			}
			return task;
		} catch (NoSuchElementException e) {
			return null;
		}
	}

	public void ungetTask(TwoACExperimentTask t) {
		if (logger.isDebugEnabled()) {
			logger.debug("	Unget -- Generation: " + t.getGenId() + " task: "
					+ t.getTaskId());
		}

		if (t == null)
			return;

		LinkedList<TwoACExperimentTask> tasks = currentGeneration.get();
		if (tasks == null) {
			return;
		}

		TwoACExperimentTask cur;
		try {
			cur = tasks.getFirst();
		} catch (NoSuchElementException e) {
			cur = null;
		}

		if (cur == null || cur.getGenId() == t.getGenId()) {
			if (ungetBehavior == UngetPolicy.HEAD) {
				tasks.addFirst(t);
			} else {
				tasks.addLast(t);
			}
		}
	}

	public void run() {
		try {
			threadHelper.started();

			while (!threadHelper.isDone()) {
				if (lastDoneTaskId < 0) {
					lastDoneTaskId = dbUtil.readTaskDoneCompleteMaxId();
				}
				GenerationInfo info = dbUtil.readReadyGenerationInfo();
				if (info.getGenId() > currentGenId) {
					// new generation found
					LinkedList<TwoACExperimentTask> taskToDo = dbUtil
							.readTwoACExperimentTasks(info.getGenId(), lastDoneTaskId);

					if (logger.isDebugEnabled()) {
						logger.debug("Generation " + info.getGenId() + " size: "
								+ taskToDo.size());
					}
					if (taskToDo.size() > 0) {
						currentGeneration.set(taskToDo);
						currentGenId = info.getGenId();
					}
				}
				try {
					Thread.sleep(queryInterval);
				} catch (InterruptedException e) {
				}
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

	public void stop() {
		if (isRunning()) {
			threadHelper.stop();
			threadHelper.join();
		}
	}

	public DbUtil getDbUtil() {
		return dbUtil;
	}

	public void setDbUtil(AllenDbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}

	public long getQueryInterval() {
		return queryInterval;
	}

	public void setQueryInterval(long queryInterval) {
		this.queryInterval = queryInterval;
	}

	public UngetPolicy getUngetBehavior() {
		return ungetBehavior;
	}

	public void setUngetBehavior(UngetPolicy ungetBehavior) {
		this.ungetBehavior = ungetBehavior;
	}

	public void start() {
		threadHelper.start();
	}
}
