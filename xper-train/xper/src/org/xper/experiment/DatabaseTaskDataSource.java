package org.xper.experiment;

import java.util.LinkedList;
import java.util.NoSuchElementException;
import java.util.concurrent.atomic.AtomicReference;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.db.vo.GenerationInfo;
import org.xper.util.DbUtil;
import org.xper.util.ThreadHelper;

public class DatabaseTaskDataSource implements TaskDataSource, Threadable {
	static Logger logger = Logger.getLogger(DatabaseTaskDataSource.class);

	public enum UngetPolicy {
		HEAD, TAIL
	};
	static final int DEFAULT_QUERY_INTERVAL = 1000;

	@Dependency
	DbUtil dbUtil;
	@Dependency
	long queryInterval = DEFAULT_QUERY_INTERVAL;
	@Dependency
	UngetPolicy ungetBehavior = UngetPolicy.HEAD;

	AtomicReference<LinkedList<ExperimentTask>> currentGeneration = new AtomicReference<LinkedList<ExperimentTask>>();
	ThreadHelper threadHelper = new ThreadHelper("DatabaseTaskDataSource", this);
	long currentGenId = -1;
	long lastDoneTaskId = -1;

	public boolean isRunning() {
		return threadHelper.isRunning();
	}

	public ExperimentTask getNextTask() {
		try {
			LinkedList<ExperimentTask> tasks = currentGeneration.get();
			if (tasks == null) {
				return null;
			}
			ExperimentTask task = tasks.removeFirst();
			if (logger.isDebugEnabled()) {
				logger.debug("	Get -- Generation: " + task.genId + " task: "
						+ task.taskId);
			}
			return task;
		} catch (NoSuchElementException e) {
			return null;
		}
	}

	public void ungetTask(ExperimentTask t) {
		if (logger.isDebugEnabled()) {
			logger.debug("	Unget -- Generation: " + t.genId + " task: "
					+ t.taskId);
		}

		if (t == null)
			return;

		LinkedList<ExperimentTask> tasks = currentGeneration.get();
		if (tasks == null) {
			return;
		}

		ExperimentTask cur;
		try {
			cur = tasks.getFirst();
		} catch (NoSuchElementException e) {
			cur = null;
		}

		if (cur == null || cur.genId == t.genId) {
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
					LinkedList<ExperimentTask> taskToDo = dbUtil
							.readExperimentTasks(info.getGenId(), lastDoneTaskId);

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

	public void setDbUtil(DbUtil dbUtil) {
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
