package org.xper.allen.nafc.blockgen;

import org.xper.allen.util.AllenDbUtil;

/**
 * All trials need to be written to the database and be associated with a taskId. 
 * @return taskId
 * @author r2_allen
 *
 */
public interface Trial {
	void preWrite();
	void write();
	Long getTaskId();
	
}
