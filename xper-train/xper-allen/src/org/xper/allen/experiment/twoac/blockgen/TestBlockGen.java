package org.xper.allen.experiment.twoac.blockgen;

import java.util.ArrayList;
import java.util.Random;

import org.xper.Dependency;
import org.xper.allen.Block;
import org.xper.allen.experiment.twoac.RewardPolicy;
import org.xper.allen.specs.BlockSpec;
import org.xper.allen.specs.GaussSpec;
import org.xper.allen.specs.SaccadeStimSpecSpec;
import org.xper.allen.specs.TwoACStimSpecSpec;
import org.xper.allen.specs.VisualStimSpecSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.allen.util.AllenXMLUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.exception.VariableNotFoundException;
import org.xper.time.TimeUtil;

public class TestBlockGen {
	@Dependency
	AllenDbUtil dbUtil;
	@Dependency
	TimeUtil globalTimeUtil;
	@Dependency
	AllenXMLUtil xmlUtil;
	
	/**
	 * Selects visual stimuli randomly from stimTypes
	 */
	Random r = new Random();
	
	public TestBlockGen() {
	}
	
	
	long genId = 1;
	
	
	public void generate() { //
	int numTrials = 100;
		
	Coordinates2D[] targetEyeWinCoords = {new Coordinates2D(-5, 0), new Coordinates2D(5,0)};	
	double[] targetEyeWinSize = {2, 2};
	long[] eStimObjData = {1};
	RewardPolicy rewardPolicy = RewardPolicy.ONE;
	
		try {
			genId = dbUtil.readReadyGenerationInfo().getGenId() + 1;
		} catch (VariableNotFoundException e) {
			dbUtil.writeReadyGenerationInfo(genId, 0);
		}
		for (int i = 0; i < numTrials; i++) {
			long sampleId = globalTimeUtil.currentTimeMicros();
			long taskId = sampleId;
			long[] choiceId = {sampleId + 1, sampleId + 2};
			
			TwoACStimSpecSpec stimSpec = new TwoACStimSpecSpec(targetEyeWinCoords, targetEyeWinSize, sampleId, choiceId, eStimObjData, rewardPolicy);
			
			String spec = stimSpec.toXml();
			System.out.println(spec);
			dbUtil.writeStimObjData(sampleId, new GaussSpec(0, -5, 3, 1).toXml(), "sample");
			dbUtil.writeStimObjData(choiceId[0], new GaussSpec(-5, 0, 3, 1).toXml(), "choice 1");
			dbUtil.writeStimObjData(choiceId[1], new GaussSpec(5, 0, 3, 1).toXml(), "choice 2");
			dbUtil.writeStimSpec(taskId, stimSpec.toXml());
			dbUtil.writeTaskToDo(taskId, taskId, -1, genId);
		
		}
		dbUtil.updateReadyGenerationInfo(genId, numTrials);
		System.out.println("Done Generating...");
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
