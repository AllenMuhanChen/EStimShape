package org.xper.acq.player;

import org.xper.db.vo.AcqDataEntry;

public interface AnalogPlayer {
	
	/**
	 * Get maximum sample index in the data.
	 *
	 */
	public int getEndSampleIndex ();
	
	/**
	 * Reset pointer to the start of the data list.
	 *
	 */
	public void reset ();
	
	/**
	 * Move pointer position to the first data record with time stamp greater than or equal to sampleIndex.
	 * 
	 * @param startTime
	 * @return
	 */
	public boolean seekBeginWith (int sampleIndex);
	
	/**
	 * Move pointer position to the last data record with time stamp less than or equal to sampleIndex.
	 * 
	 * @param startSampleIndex
	 * @return
	 */
	public boolean seekEndWith (int sampleIndex);
	
	/**
	 * Advance pointer to the data one step forward.
	 * 
	 * @return false if no more data available. Pointer position is not advanced if returning false.
	 */
	
	public boolean forward ();
	
	/**
	 * Advance the pointer to the data one step backward.
	 * 
	 * @return false if already at the head of the data. Pointer position is not changed if returning false.
	 */
	
	public boolean rewind ();
	
	/**
	 * Return the internal pointer position of the data.
	 * @return
	 */
	public int getPosition ();
	
	/**
	 * 
	 * @return null if end of data is already reached.
	 */
	public AcqDataEntry next ();
	
	/**
	 * 
	 * @return null if already at the start of the data list.
	 */
	public AcqDataEntry prev ();
	
	/**
	 * Get the current data entry.
	 * 
	 * @return
	 */
	public AcqDataEntry getData ();
	
	/**
	 * Get the data entry at pos.
	 * 
	 * @param pos
	 * @return
	 */
	public AcqDataEntry getData (int pos);
}
