package org.xper.allen.nafc.experiment;

import java.util.LinkedList;
import java.util.NoSuchElementException;
import java.util.Random;
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
	@Dependency
	int ungetTaskThreshold;
	@Dependency
	boolean pruneDeletedTasks = true;

	AtomicReference<LinkedList<NAFCExperimentTask>> currentGeneration = new AtomicReference<LinkedList<NAFCExperimentTask>>();
	ThreadHelper threadHelper = new ThreadHelper("DatabaseTaskDataSource", this);
	long currentGenId = -1;
	long lastDoneTaskId = -1;

	/**
	 * Guards compound read/modify operations on the queue held in
	 * {@link #currentGeneration}. Shared by {@link #getNextTask()},
	 * {@link #ungetTask(NAFCExperimentTask)} and the prune/append steps in
	 * {@link #run()} so that pruning deleted tasks cannot corrupt the list while
	 * the experiment thread is taking from it.
	 */
	private final Object queueLock = new Object();

	public boolean isRunning() {
		return threadHelper.isRunning();
	}

	public NAFCExperimentTask getNextTask() {
		synchronized (queueLock) {
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
	}

	public void ungetTask(NAFCExperimentTask t) {
		System.out.println("UNGOT!");
		if (logger.isDebugEnabled()) {
			logger.debug("	Unget -- Generation: " + t.getGenId() + " task: "
					+ t.getTaskId());
		}

		if (t == null)
			return;

		synchronized (queueLock) {
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
				if (tasks.size() >= ungetTaskThreshold) {
					if (ungetBehavior == UngetPolicy.HEAD) {
						tasks.addFirst(t);
					} else if (ungetBehavior == UngetPolicy.TAIL) {
						tasks.addLast(t);
					} else {
						int numTasks = tasks.size();
						Random r = new Random();
						int randIndex;
						if (numTasks > 0) {
							randIndex = r.nextInt(numTasks);
						} else {
							randIndex = 0;
						}

						tasks.add(randIndex, t);
					}
				} else{
					System.out.println("Did not Unget Task because number of tasks does not exceed threshold");
				}
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
						/////////////////////////
						synchronized (queueLock) {
							LinkedList<NAFCExperimentTask> unfinished = currentGeneration.get();
							if(unfinished==null){
								unfinished = new LinkedList<>();
							}
							unfinished.addAll(taskToDo);
							currentGeneration.set(unfinished);
						}
						currentGenId = info.getGenId();
					}
				}

				// Reconcile the in-memory queue against TaskToDo so that tasks deleted
				// from the DB while a generation is ongoing are dropped from the queue.
				// Removal-only: we never re-add, so already-served/completed tasks are
				// unaffected (they are no longer in the queue).
				if (pruneDeletedTasks) {
					pruneDeletedTasks();
				}

				try {
					Thread.sleep(queryInterval);
				} catch (InterruptedException ignored) {
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

	/**
	 * Removes from the in-memory queue any task whose row no longer exists in
	 * TaskToDo. The (potentially blocking) DB read is done outside {@link #queueLock};
	 * only the fast in-memory reconciliation is done under the lock so the experiment
	 * thread is not stalled by the query.
	 */
	private void pruneDeletedTasks() {
		// Snapshot the generations currently represented in the queue.
		java.util.Set<Long> genIds;
		synchronized (queueLock) {
			LinkedList<NAFCExperimentTask> tasks = currentGeneration.get();
			if (tasks == null || tasks.isEmpty()) {
				return;
			}
			genIds = new java.util.HashSet<Long>();
			for (NAFCExperimentTask t : tasks) {
				genIds.add(t.getGenId());
			}
		}

		// Read the live set of task ids from the DB (no lock held).
		java.util.Set<Long> aliveIds = new java.util.HashSet<Long>();
		for (Long genId : genIds) {
			aliveIds.addAll(dbUtil.readTaskToDoIds(genId, lastDoneTaskId));
		}

		// Drop queued tasks that have disappeared from TaskToDo. Only consider
		// generations we actually queried, so a generation appended concurrently
		// (whose ids we did not read) is never mistakenly pruned.
		synchronized (queueLock) {
			LinkedList<NAFCExperimentTask> tasks = currentGeneration.get();
			if (tasks == null) {
				return;
			}
			int before = tasks.size();
			java.util.Iterator<NAFCExperimentTask> it = tasks.iterator();
			while (it.hasNext()) {
				NAFCExperimentTask task = it.next();
				if (genIds.contains(task.getGenId()) && !aliveIds.contains(task.getTaskId())) {
					it.remove();
				}
			}
			int removed = before - tasks.size();
			if (removed > 0) {
				logger.info("Pruned " + removed + " task(s) deleted from TaskToDo");
				System.out.println("Pruned " + removed + " task(s) deleted from TaskToDo");
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

	public int getUngetTaskThreshold() {
		return ungetTaskThreshold;
	}

	public void setUngetTaskThreshold(int ungetTaskThreshold) {
		this.ungetTaskThreshold = ungetTaskThreshold;
	}

	public boolean isPruneDeletedTasks() {
		return pruneDeletedTasks;
	}

	public void setPruneDeletedTasks(boolean pruneDeletedTasks) {
		this.pruneDeletedTasks = pruneDeletedTasks;
	}
}