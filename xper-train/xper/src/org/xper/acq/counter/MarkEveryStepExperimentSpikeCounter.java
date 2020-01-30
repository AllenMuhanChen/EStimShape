package org.xper.acq.counter;

import java.util.List;
import java.util.Map;
import java.util.SortedMap;
import java.util.TreeMap;

import org.xper.Dependency;
import org.xper.acq.player.DigitalPlayer;
import org.xper.acq.vo.DigitalChannel;
import org.xper.db.vo.AcqDataEntry;
import org.xper.db.vo.AcqSessionEntry;
import org.xper.db.vo.GenerationTaskDoneList;
import org.xper.db.vo.SystemVariable;
import org.xper.db.vo.TaskDoneEntry;
import org.xper.util.AcqUtil;
import org.xper.util.DbUtil;

public class MarkEveryStepExperimentSpikeCounter {
	@Dependency
	DbUtil dbUtil;

	public void setDbUtil(DbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}
	
	public SortedMap<Long, MarkEveryStepTaskSpikeDataEntry> getTaskSpikeByGeneration(
			long genId, int dataChan) {
		return getTaskSpikeByGeneration(genId, dataChan, Integer.MAX_VALUE);
	}

	/**
	 * Only results for completed tasks are included.
	 * 
	 * @param genId
	 * @param dataChan
	 * @return
	 */
	public SortedMap<Long, MarkEveryStepTaskSpikeDataEntry> getTaskSpikeByGeneration(
			long genId, int dataChan, int maxStages) {
		GenerationTaskDoneList taskDone = dbUtil
				.readTaskDoneByGeneration(genId);
		return getTaskSpike(taskDone.getDoneTasks(), dataChan, maxStages);
	}
	
	public SortedMap<Long, MarkEveryStepTaskSpikeDataEntry> getTaskSpike(
			List<TaskDoneEntry> tasks, int dataChan) {
		return getTaskSpike(tasks, dataChan, Integer.MAX_VALUE);
	}

	public SortedMap<Long, MarkEveryStepTaskSpikeDataEntry> getTaskSpike(
			List<TaskDoneEntry> tasks, int dataChan, int maxStages) {
		SortedMap<Long, MarkEveryStepTaskSpikeDataEntry> ret = new TreeMap<Long, MarkEveryStepTaskSpikeDataEntry>();
		if (tasks.size() <= 0)
			return ret;

		Map<String, SystemVariable> var = dbUtil.readSystemVar("acq_%", tasks
				.get(0).getTstamp());
		int even_marker_chan = Integer.parseInt(var.get("acq_even_marker_chan")
				.getValue(0));
		int odd_marker_chan = Integer.parseInt(var.get("acq_odd_marker_chan")
				.getValue(0));
		DigitalPlayer.Type data_channel_type = DigitalChannel
				.stringToDataPlayerType(var.get("acq_channel_type").getValue(
						dataChan));
		DigitalPlayer.Type even_marker_channel_type = DigitalChannel
				.stringToDataPlayerType(var.get("acq_channel_type").getValue(
						even_marker_chan));
		DigitalPlayer.Type odd_marker_channel_type = DigitalChannel
				.stringToDataPlayerType(var.get("acq_channel_type").getValue(
						odd_marker_chan));
		double freq = Double.parseDouble(var.get("acq_master_frequency")
				.getValue(0));

		for (TaskDoneEntry task : tasks) {
//			System.out.println("Task ID = " + task.getTaskId());
			MarkEveryStepTaskSpikeDataEntry spike = getTaskSpike(task, dataChan,
					even_marker_chan, odd_marker_chan, data_channel_type,
					even_marker_channel_type, odd_marker_channel_type, freq, maxStages);
			ret.put(task.getTaskId(), spike);
//			System.out.println("Task ID = " + task.getTaskId() + "done");
		}

		return ret;
	}

	protected MarkEveryStepTaskSpikeDataEntry getTaskSpike(TaskDoneEntry task,
			int dataChan, int evenMarkerChan, int oddMarkerChan,
			DigitalPlayer.Type dataChannelType,
			DigitalPlayer.Type evenMarkerChannelType,
			DigitalPlayer.Type oddMarkerChannelType, double freq, int maxStages) {

		AcqSessionEntry acq_session = dbUtil.readAcqSession(task.getTstamp());
		
		List<AcqDataEntry> acq_data = dbUtil.readAcqData(acq_session.getStartTime(), acq_session.getStopTime());
		
		if (acq_data.size() <= 0) {
//			throw new InvalidAcqDataException("No AcqData find for task " + task.getTaskId());
			System.out.println("No AcqData find for task " + task.getTaskId());
		}

		MarkEveryStepTaskSpikeDataEntry ent = new MarkEveryStepTaskSpikeDataEntry();
		ent.setTaskId(task.getTaskId());
		ent.setSampleFrequency(freq);
		
		SessionSpikeData sessionSpike = AcqUtil.countSessionSpike(acq_data, 
				dataChan, evenMarkerChan, oddMarkerChan, 
				dataChannelType, evenMarkerChannelType, oddMarkerChannelType, freq, maxStages);
		ent.setTrialStageData(sessionSpike.getTrialStageData());
		ent.setSpikePerSec(sessionSpike.getSpikePerSec());

		return ent;
	}
}
