package org.xper.db.vo;

import java.util.List;


public class GenerationTaskToDoList {
	/**
	 * Generation ID. Staring from 1 and increasing.
	 */
	long genId;
	List<TaskToDoEntry> tasks;
	
	/**
	 * Number of tasks in the list.
	 * 
	 * @return number of tasks.
	 */
	public int size () {
		return tasks.size();
	}
	
	/**
	 * Get task from index.
	 * 
	 * @param index
	 * @return {@link TaskToDoEntry}
	 */
	
	public TaskToDoEntry getTask (int index) {
		return tasks.get(index);
	}
	
	/**
	 * Convert the list to array.
	 * 
	 * @return Array of {@link TaskToDoEntry}
	 */
	
	public TaskToDoEntry [] toArray () {
		int size = size ();
		TaskToDoEntry [] result = new TaskToDoEntry[size];
		for (int i = 0; i < size; i ++) {
			result[i] = tasks.get(i);
		}
		return result;
	}

	public long getGenId() {
		return genId;
	}

	public void setGenId(long genId) {
		this.genId = genId;
	}

	public List<TaskToDoEntry> getTasks() {
		return tasks;
	}

	public void setTasks(List<TaskToDoEntry> tasks) {
		this.tasks = tasks;
	}
}
