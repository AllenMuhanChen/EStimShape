package org.xper.allen.nafc.experiment;

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

public class NAFCDatabaseTaskDataSource extends DatabaseTaskDataSource {
	static Logger logger = Logger.getLogger(DatabaseTaskDataSource.class);

	static final int DEFAULT_QUERY_INTERVAL = 1000;

	@Dependency
	AllenDbUtil dbUtil;
	@Dependency
	long queryInterval = DEFAULT_QUERY_INTERVAL;
	@Dependency
	UngetPolicy ungetBehavior;

	AtomicReference<LinkedList<NAFCExperimentTask>> currentGeneration = new AtomicReference<LinkedList<NAFCExperimentTask>>();
	ThreadHelper threadHelper = new ThreadHelper("DatabaseTaskDataSource", this);
	long currentGenId = -1;
	long lastDoneTaskId = -1;

	public boolean isRunning() {
		return threadHelper.isRunning();
	}

	public NAFCExperimentTask getNextTask() {
		try {
			LinkedList<NAFCExperimentTask> tasks = currentGeneration.get();
			if (tasks == null) {
				return null;
			}
			NAFCExperimentTask task = tasks.removeFirst();
			if (logger.isDebugEnabled()) {
				logger.debug("	Get -- Generation: " + task.getGenId() + " task: "
						+ task.getTaskId());
			}
			return task;
		} catch (NoSuchElementException e) {
			return null;
		}
	}

	public void ungetTask(NAFCExperimentTask t) {
		System.out.println("UNGOT!");
		if (logger.isDebugEnabled()) {
			logger.debug("	Unget -- Generation: " + t.getGenId() + " task: "
					+ t.getTaskId());
		}

		if (t == null)
			return;

		LinkedList<NAFCExperimentTask> tasks = currentGeneration.get();
		if (tasks == null) {
			return;
		}

		NAFCExperimentTask cur;
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

	/**
	 * Edited by AC:
	 * Modified so when a new generation is received, we append the remaining task lists to the new one.
	 * Effect is that current generation is finished before moving onto stimuli of next generation. 
	 */
	public void run() {
		try {
			threadHelper.started();

			while (!threadHelper.isDone()) {
				if (lastDoneTaskId < 0) {
					lastDoneTaskId = dbUtil.readTaskDoneCompleteMaxId();
				}
				GenerationInfo info = dbUtil.readReadyGenerationInfo();
				//System.out.println("readyGenerationInfo: " + info.getGenId());
				if (info.getGenId() > currentGenId) {
					// new generation found
					LinkedList<NAFCExperimentTask> taskToDo = dbUtil
							.readNAFCExperimentTasks(info.getGenId(), lastDoneTaskId);

					if (logger.isDebugEnabled()) {
						logger.debug("Generation " + info.getGenId() + " size: "
								+ taskToDo.size());
					}
					if (taskToDo.size() > 0) {
						//AC Addition: Finish previous gen/block before moving to the next
						LinkedList<NAFCExperimentTask> currentTaskToDo = currentGeneration.get();
						try {
							taskToDo.addAll(currentTaskToDo);
						}catch (Exception e) {

						}
						/////////////////////////
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