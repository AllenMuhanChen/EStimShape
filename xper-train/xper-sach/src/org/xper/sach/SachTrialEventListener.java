package org.xper.sach;


import org.xper.classic.TrialEventListener;
import org.xper.sach.vo.SachTrialContext;

public interface SachTrialEventListener extends TrialEventListener {
	public void targetOn (long timestamp, SachTrialContext context);
	//public void targetInitialSelection(long timestamp, SachTrialContext context);
	public void targetSelectionSuccess(long timestamp, SachTrialContext context);
	
	// added by shs for behavioral tracking:
	public void trialPASS(long timestamp, SachTrialContext context);
	public void trialFAIL(long timestamp, SachTrialContext context);
	public void trialBREAK(long timestamp, SachTrialContext context);
	public void trialNOGO(long timestamp, SachTrialContext context);
}
