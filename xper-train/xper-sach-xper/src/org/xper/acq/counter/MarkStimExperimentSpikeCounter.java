package org.xper.acq.counter;

import java.util.List;
import java.util.Map;
import java.util.SortedMap;
import java.util.TreeMap;

import org.xper.Dependency;
import org.xper.acq.player.DigitalChannelPlayer;
import org.xper.acq.player.DigitalPlayer;
import org.xper.acq.vo.DigitalChannel;
import org.xper.db.vo.AcqDataEntry;
import org.xper.db.vo.AcqSessionEntry;
import org.xper.db.vo.GenerationTaskDoneList;
import org.xper.db.vo.SystemVariable;
import org.xper.db.vo.TaskDoneEntry;
import org.xper.exception.InvalidAcqDataException;
import org.xper.util.AcqUtil;
import org.xper.util.DbUtil;

public class MarkStimExperimentSpikeCounter {
	@Dependency
	DbUtil dbUtil;

	public void setDbUtil(DbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}

	/**
	 * Skip tasks done before until_task_id.
	 * 
	 * @param player
	 * @param acq_session
	 * @param until_task_id
	 * @return Return the position of the first task with id greater than or equal to until_task_id
	 */
	protected void skipTask (DigitalChannelPlayer[] player, AcqSessionEntry acq_session, long until_task_id) {
		int [] pos = new int[]{-1, -1};
		int prev_task_ind = 0;
		// skip tasks until until_task_id
		List<TaskDoneEntry> prev_tasks = dbUtil.readTaskDoneByTimestampRange(acq_session.getStartTime(), acq_session.getStopTime());
		boolean sessionDone = false;
		while (prev_tasks.get(prev_task_ind).getTaskId() < until_task_id) {
			if (sessionDone) 
				throw new InvalidAcqDataException ("Not enough AcqData while skipping prior generation task " + 
						prev_tasks.get(prev_task_ind).getTaskId() + 
						": session (" + acq_session.getStartTime() + "," + acq_session.getStopTime() + ")");
			sessionDone = AcqUtil.taskAdvance (player, pos);
			prev_task_ind ++;
		}
	}
	
	/**
	 * Get the task spike info for the generation genId.
	 * 
	 * @param genId
	 * @param data_chan
	 * @param leftMove Move the left edge of the stimulus data frame in ms, can be negative or positive to account for response latency, stabalization time et al.
	 * @param rightMove Move the right edge of the stimulus data frame in ms, can be negative or positive to account for response latency, stabalization time et al.
	 * @return
	 */
	public SortedMap<Long, TaskSpikeDataEntry> getTaskSpikeByGeneration (long genId, int data_chan, double leftMove, double rightMove) {
		GenerationTaskDoneList taskDone = dbUtil.readTaskDoneByGeneration(genId);
		return getTaskSpike(taskDone.getDoneTasks(), data_chan, leftMove, rightMove);
	}
	
	/**
	 * Get task spike info for tasks with id between minId and maxId.
	 * 
	 * @param minId
	 * @param maxId
	 * @param data_chan
	 * @param leftMove Move the left edge of the stimulus data frame in ms, can be negative or positive to account for response latency, stabalization time et al.
	 * @param rightMove Move the right edge of the stimulus data frame in ms, can be negative or positive to account for response latency, stabalization time et al.
	 * @return
	 */
	public SortedMap<Long, TaskSpikeDataEntry> getTaskSpikeByIdRange (long minId, long maxId, int data_chan, double leftMove, double rightMove) {
		List<TaskDoneEntry> taskDone = dbUtil.readTaskDoneByIdRange(minId, maxId);
		return getTaskSpike(taskDone, data_chan, leftMove, rightMove);
	}
	
	/**
	 * Get task spike info for tasks done between startTime and stopTime.
	 * 
	 * @param startTime
	 * @param stopTime
	 * @param data_chan
	 * @param leftMove Move the left edge of the stimulus data frame in ms, can be negative or positive to account for response latency, stabalization time et al.
	 * @param rightMove Move the right edge of the stimulus data frame in ms, can be negative or positive to account for response latency, stabalization time et al.
	 * @return
	 */
	
	public SortedMap<Long, TaskSpikeDataEntry> getTaskSpikeByTimestampRange (long startTime, long stopTime, int data_chan, double leftMove, double rightMove) {
		List<TaskDoneEntry> taskDone = dbUtil.readTaskDoneByTimestampRange(startTime, stopTime);
		return getTaskSpike(taskDone, data_chan, leftMove, rightMove);
	}
	
	/**
	 * Get the spike information from data_chan for tasks in taskDone.
	 * 
	 * @param taskDone
	 * @param data_chan
	 * @param leftMove Move the left edge of the stimulus data frame in ms, can be negative or positive to account for response latency, stabalization time et al.
	 * @param rightMove Move the right edge of the stimulus data frame in ms, can be negative or positive to account for response latency, stabalization time et al.
	 * @return Map task_id to TaskSpikeDataEntry
	 */
	public SortedMap<Long, TaskSpikeDataEntry> getTaskSpike (List<TaskDoneEntry> taskDone, int data_chan, double leftMove, double rightMove) {
		
		SortedMap<Long, TaskSpikeDataEntry> ret = new TreeMap<Long, TaskSpikeDataEntry>();
		
		int task_num = taskDone.size();
		int task_ind = 0; 
		
		if (task_num <= 0) return ret;

		Map<String, SystemVariable> var = dbUtil.readSystemVar("acq_%", taskDone.get(task_ind).getTstamp());
		int even_marker_chan = Integer.parseInt(var.get("acq_even_marker_chan").getValue(0));
		int odd_marker_chan = Integer.parseInt(var.get("acq_odd_marker_chan").getValue(0));
		DigitalPlayer.Type data_channel_type = DigitalChannel.stringToDataPlayerType(var.get("acq_channel_type").getValue(data_chan));
		DigitalPlayer.Type even_marker_channel_type = DigitalChannel.stringToDataPlayerType(var.get("acq_channel_type").getValue(even_marker_chan));
		DigitalPlayer.Type odd_marker_channel_type = DigitalChannel.stringToDataPlayerType(var.get("acq_channel_type").getValue(odd_marker_chan));
		double freq = Double.parseDouble(var.get("acq_master_frequency").getValue(0));
		
		while (task_ind < task_num) {
			AcqSessionEntry acq_session;
			List<AcqDataEntry> acq_data;
			DigitalChannelPlayer data_player;
			DigitalChannelPlayer even_marker_player;
			DigitalChannelPlayer odd_marker_player;

			// Get Data
			acq_session = dbUtil.readAcqSession(taskDone.get(task_ind).getTstamp());
			acq_data = dbUtil.readAcqData(acq_session.getStartTime(), acq_session.getStopTime());
			
			if (acq_data.size () <= 0) {
				throw new InvalidAcqDataException("No AcqData find for task " + taskDone.get(task_ind).getTaskId());
			}
			
			// Get the players
			data_player = AcqUtil.getDigitalPlayer (acq_data, data_chan, data_channel_type);
			even_marker_player = AcqUtil.getDigitalPlayer (acq_data, even_marker_chan, even_marker_channel_type);
			odd_marker_player = AcqUtil.getDigitalPlayer (acq_data, odd_marker_chan, odd_marker_channel_type);
			if (!even_marker_player.hasUp() || !odd_marker_player.hasUp() ||
					!even_marker_player.hasDown() || !odd_marker_player.hasDown()) {
				throw new InvalidAcqDataException("Even and odd marker channels must record up and down edge.");
			}
			DigitalChannelPlayer [] player = new DigitalChannelPlayer[] {even_marker_player, odd_marker_player};
		
			int [] pos = new int[] {-1, -1};

			// Acq data may contain tasks done before the first task in taskDone.
			if (task_ind == 0) {
				skipTask (player, acq_session, taskDone.get(0).getTaskId());
			}

			// calculate spike rate from data
			boolean sessionDone = false;
			while (task_ind < task_num && taskDone.get(task_ind).getTstamp() <= acq_session.getStopTime()) {
				if (sessionDone) 
					throw new InvalidAcqDataException ("Not enough AcqData for task " + taskDone.get(task_ind).getTaskId() +
							": session (" + acq_session.getStartTime() + "," + acq_session.getStopTime() + ")");
				sessionDone = AcqUtil.taskAdvance (player, pos);
				TaskSpikeDataEntry ent = AcqUtil.countSpike (data_player, pos, freq, leftMove, rightMove);
				ent.taskId = taskDone.get(task_ind).getTaskId();
				ret.put(new Long(ent.taskId), ent);

				task_ind ++;
			} // while this acq_session

		} // while task_ind < task_num
		return ret;
	}
}
