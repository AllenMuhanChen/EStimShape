package org.xper.sach.acq.counter;

import java.util.List;
import java.util.SortedMap;
import java.util.TreeMap;

import org.xper.Dependency;
import org.xper.acq.counter.MarkEveryStepExperimentSpikeCounter;
import org.xper.acq.counter.MarkEveryStepTaskSpikeDataEntry;
import org.xper.acq.counter.TrialStageData;
import org.xper.db.vo.GenerationTaskDoneList;
import org.xper.db.vo.TaskDoneEntry;
import org.xper.sach.expt.SachExptSpec;
import org.xper.sach.util.SachDbUtil;
import org.xper.sach.util.SachMathUtil;


public class SachMarkEveryStepExptSpikeCounter extends MarkEveryStepExperimentSpikeCounter {	
	@Dependency
	SachDbUtil dbUtil;
	
	// added by SHS for fake spikes:
	
	public SortedMap<Long, MarkEveryStepTaskSpikeDataEntry> getFakeTaskSpikeByGeneration(long genId) {
		GenerationTaskDoneList taskDone = dbUtil.readTaskDoneByGeneration(genId);
		return getFakeTaskSpike(taskDone.getDoneTasks());
	}
	
	public SortedMap<Long, MarkEveryStepTaskSpikeDataEntry> getFakeTaskSpike(List<TaskDoneEntry> tasks) {
		SortedMap<Long, MarkEveryStepTaskSpikeDataEntry> ret = new TreeMap<Long, MarkEveryStepTaskSpikeDataEntry>();
		if (tasks.size() <= 0) return ret;

		for (TaskDoneEntry task : tasks) {
			long taskId = task.getTaskId();
			MarkEveryStepTaskSpikeDataEntry spike = new MarkEveryStepTaskSpikeDataEntry();
			spike.setTaskId(taskId);
			
			// get number of stims in a task/trial:
			SachExptSpec trialSpec = SachExptSpec.fromXml(dbUtil.readStimSpec(dbUtil.getStimIdByTaskId(taskId)).getSpec());
			int numStims = trialSpec.getStimObjIdCount();
			
			// for each stim add spike info:
			for (int n=0;n<numStims;n++) { // *** I'm assuming there are only numStim epochs and the first one is 0 --- NO, I THINK THIS IS WRONG, MANY EPOCHS (fixation, stimuli, ISIs, target, etc)
				spike.addSpikePerSec(SachMathUtil.randRange(30, 1));	// add random spike rate
				
				TrialStageData d = new TrialStageData();
				spike.addTrialStageData(d);
			}
			
			ret.put(taskId, spike);
		}

		return ret;
	}
	
	public void setDbUtilSach(SachDbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}
	
	
}
