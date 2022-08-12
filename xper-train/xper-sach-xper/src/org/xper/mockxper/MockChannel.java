package org.xper.mockxper;

import java.util.List;
import java.util.Map;

import org.xper.db.vo.AcqDataEntry;
import org.xper.db.vo.SystemVariable;
import org.xper.db.vo.TaskSpikeRate;

public interface MockChannel {
	/**
	 * 
	 * @param task
	 * @param systemVar
	 * @return
	 */
	public List<AcqDataEntry> getData(TaskSpikeRate task, Map<String, SystemVariable> systemVar);
	
	public void sessionInit ();
	
	public static final int INIT_SAMPLE_INDEX = 1000;
	
	public static final int REFRESH_RATE = 75;
}
