package org.xper.sach.vo;

import org.xper.db.vo.TaskDoneEntry;
import org.xper.experiment.BatchTaskDoneCache;
import org.xper.experiment.ExperimentTask;
import org.xper.util.DbUtil;

import com.mysql.jdbc.TimeUtil;

public class SachBatchTaskDoneCache extends BatchTaskDoneCache {

	DbUtil dbUtil = super.getDbUtil();
	TimeUtil timeUtil;
	
	public SachBatchTaskDoneCache(int batchSize) {
		super(batchSize);
		// TODO Auto-generated constructor stub
	}
	
	public void put(ExperimentTask task, long timestamp, boolean partial) {
		// finsih this. need to record local timestamp and also extend TaskDoneEntry to handle this
		// then need to add to the config file(s!
		// also need to change/addto SachTrialExperimentUtil, SachDbUtil... ugh!
		// --> if I don't want to change TaskDoneCache interface, then I need access to 
		// 	   "state.setLocalTimeUtil(baseConfig.localTimeUtil())" here. set in config file.
		//     (initialize timeUtil, setter & getter)
		//long timestamp_local = timeUtil.currentTimeMicros()
		TaskDoneEntry ent = new TaskDoneEntry();
		ent.setTaskId(task.getTaskId());
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

	@Override
	public void flush() {
		if (index > 0) {
			dbUtil.writeTaskDoneBatch(cache, index);	// would need to make diff version of this
			index = 0;
			cache = new TaskDoneEntry[batchSize];
		}
	}
}
