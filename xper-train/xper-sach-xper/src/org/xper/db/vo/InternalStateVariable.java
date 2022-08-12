package org.xper.db.vo;

import java.util.List;

public class InternalStateVariable {
	String name;
	/**
	 * order by arr_ind
	 */
	List<String> values;
	
	/**
	 * Get the value for index.
	 * 
	 * @param index
	 * @return value as string.
	 */
	public String getValue(int index) {
		return values.get(index);
	}
	
	/**
	 * Convert to array.
	 * 
	 * @return Array of values as string.
	 */
	public String [] getValueArray () {
		int size = values.size();
		String [] result = new String [size];
		for (int i = 0; i < size; i ++) {
			result[i] = values.get(i);
		}
		return result;
	}

	public String getName() {
		return name;
	}

	public void setName(String name) {
		this.name = name;
	}

	public List<String> getValues() {
		return values;
	}

	public void setValues(List<String> values) {
		this.values = values;
	}
}
