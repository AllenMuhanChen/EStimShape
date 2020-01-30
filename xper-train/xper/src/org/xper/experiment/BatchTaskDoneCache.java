package org.xper.experiment;

import org.xper.Dependency;
import org.xper.db.vo.TaskDoneEntry;
import org.xper.util.DbUtil;

public class BatchTaskDoneCache implements TaskDoneCache {
	@Dependency
	protected
	int batchSize;
	@Dependency
	protected
	DbUtil dbUtil;
	
	protected TaskDoneEntry[] cache;
	protected int index = 0;

	public BatchTaskDoneCache(int batchSize) {
		this.batchSize = batchSize;
		cache = new TaskDoneEntry[batchSize];
	}

	public void put(ExperimentTask task, long timestamp, boolean partial) {
		TaskDoneEntry ent = new TaskDoneEntry();
		ent.setTaskId(task.taskId);
		ent.setTstamp(timestamp);
		if (partial) {
			ent.setPart_done(1);
		} else {
			ent.setPart_done(0);
		}
		cache[index] = ent;
		index++;
		if (index == cache.length) {
			dbUtil.writeTaskDoneBatch(cache, batchSize);
			index = 0;
			cache = new TaskDoneEntry[batchSize];
		}
	}

	public void flush() {
		if (index > 0) {
			dbUtil.writeTaskDoneBatch(cache, index);
			index = 0;
			cache = new TaskDoneEntry[batchSize];
		}
	}

	public DbUtil getDbUtil() {
		return dbUtil;
	}

	public void setDbUtil(DbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}
}
