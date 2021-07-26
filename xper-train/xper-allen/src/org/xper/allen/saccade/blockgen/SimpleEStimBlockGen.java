package org.xper.allen.saccade.blockgen;

import java.util.ArrayList;

import org.xper.Dependency;
import org.xper.allen.specs.SaccadeStimSpecSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.allen.util.AllenXMLUtil;
import org.xper.exception.VariableNotFoundException;
import org.xper.time.TimeUtil;

public class SimpleEStimBlockGen {
	@Dependency
	AllenDbUtil dbUtil;
	@Dependency
	TimeUtil globalTimeUtil;
	@Dependency
	AllenXMLUtil xmlUtil;
	
	long genId = 1;
	public void generate(String filepath) {
		
		ArrayList<Trial> trials = (ArrayList<Trial>) xmlUtil.parseFile(filepath);
		try {
			genId = dbUtil.readReadyGenerationInfo().getGenId() + 1;
		} catch (VariableNotFoundException e) {
			dbUtil.writeReadyGenerationInfo(genId, 0);
		}
		
		for (int i = 0; i < trials.size(); i++) {
			long taskId = globalTimeUtil.currentTimeMicros();
			Trial trial = trials.get(i);
			String spec = trial.toXml();
			System.out.println(spec);
			dbUtil.writeStimObjData(taskId, trial.getGaussSpec().toXml(), trial.getData());
			dbUtil.writeEStimObjData(taskId, trial.getEStimSpec());	
			SaccadeStimSpecSpec stimSpec = new SaccadeStimSpecSpec(trial.getTargetEyeWinCoords(), trial.getTargetEyeWinSize(), trial.getDuration(), taskId, taskId);
			dbUtil.writeStimSpec(taskId,stimSpec.toXml());
			dbUtil.writeTaskToDo(taskId, taskId, -1, genId);
		}
		dbUtil.updateReadyGenerationInfo(genId, trials.size());
		System.out.println("Done Generating");
		return;
	}
	
	public AllenDbUtil getDbUtil() {
		return dbUtil;
	}

	public void setDbUtil(AllenDbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}
	
	public TimeUtil getGlobalTimeUtil() {
		return globalTimeUtil;
	}

	public void setGlobalTimeUtil(TimeUtil globalTimeUtil) {
		this.globalTimeUtil = globalTimeUtil;
	}
	
	public AllenXMLUtil getXmlUtil() {
		return xmlUtil;
	}

	public void setXmlUtil(AllenXMLUtil xmlUtil) {
		this.xmlUtil = xmlUtil;
	}
}
