package org.xper.sach;


import org.xper.classic.MarkEveryStepTrialDrawingController;
import org.xper.classic.vo.TrialContext;
import org.xper.experiment.ExperimentTask;
import org.xper.sach.util.SachExperimentUtil;
import org.xper.sach.vo.SachTrialContext;

public class DefaultSachTrialDrawingController extends
		MarkEveryStepTrialDrawingController {
	
	/*public void slideFinish(ExperimentTask task, TrialContext context) {
		taskScene.nextMarker();
		taskScene.drawBlank(context, true, true);
		window.swapBuffers();
	}*/
	
	public void showTarget(ExperimentTask task, TrialContext context) {
		taskScene.nextMarker();
		
		if (taskScene instanceof SachTaskScene && SachExperimentUtil.isTargetOn((SachTrialContext)context)) {
			((SachTaskScene)taskScene).drawTargetScene(context);
		} else {
			taskScene.drawBlank(context, true, true);
		}
		
		getWindow().swapBuffers();
	}
	
	public void targetSelectionDone(ExperimentTask task, TrialContext context) {
		taskScene.nextMarker();
		taskScene.drawBlank(context, true, true);
		getWindow().swapBuffers();
	}
}
