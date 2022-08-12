package org.xper.db.vo;

import java.util.List;

public class GenerationTaskDoneList {
	long genId;
	List<TaskDoneEntry> doneTasks;
	
	/**
	 * Number of tasks in the list.
	 * 
	 * @return number of tasks.
	 */
	public int size () {
		return doneTasks.size();
	}
	
	/**
	 * Get task from index.
	 * 
	 * @param index
	 * @return {@link TaskDoneEntry}
	 */
	public TaskDoneEntry getTask(int index) {
		return doneTasks.get(index);
	}
	
	/**
	 * Convert the list to array.
	 * 
	 * @return Array of {@link TaskDoneEntry}
	 */
	public TaskDoneEntry [] toArray () {
		int size = size ();
		TaskDoneEntry [] result = new TaskDoneEntry[size];
		for (int i = 0; i < size; i ++) {
			result[i] = doneTasks.get(i);
		}
		return result;
	}

	public long getGenId() {
		return genId;
	}

	public void setGenId(long genId) {
		this.genId = genId;
	}

	public List<TaskDoneEntry> getDoneTasks() {
		return doneTasks;
	}

	public void setDoneTasks(List<TaskDoneEntry> doneTasks) {
		this.doneTasks = doneTasks;
	}
}
