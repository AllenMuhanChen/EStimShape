package org.xper.allen;

import org.xper.allen.nafc.blockgen.NAFCTrialParameters;

/**
 * All stims need to have a stimSpec and stimId that's written to the database.
 * @return taskId
 * @author r2_allen
 *
 */
public interface Stim {
	public void preWrite();
	public void writeStim();
	public Long getStimId();
}