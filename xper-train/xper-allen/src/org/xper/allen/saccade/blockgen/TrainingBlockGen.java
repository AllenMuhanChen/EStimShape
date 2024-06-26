package org.xper.allen.saccade.blockgen;

import java.util.ArrayList;
import java.util.Random;

import org.xper.Dependency;
import org.xper.allen.specs.BlockSpec;
import org.xper.allen.specs.SaccadeStimSpecSpec;
import org.xper.allen.specs.VisualStimSpecSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.allen.util.AllenXMLUtil;
import org.xper.exception.VariableNotFoundException;
import org.xper.time.TimeUtil;

public class TrainingBlockGen {
	@Dependency
	AllenDbUtil dbUtil;
	@Dependency
	TimeUtil globalTimeUtil;
	@Dependency
	AllenXMLUtil xmlUtil;
	
	int num_per_chan;
	long blockId;
	BlockSpec blockspec;
	Block block;
	char[] trialTypeList;
	/**
	 * Selects visual stimuli randomly from stimTypes
	 */
	Random r = new Random();
	
	public TrainingBlockGen() {
	}
	
	
	long genId = 1;
	public void generate(String filepath) { //
	
		ArrayList<TrainingTrial> visualTrials = (ArrayList<TrainingTrial>) xmlUtil.parseFile(filepath);
		try {
			genId = dbUtil.readReadyGenerationInfo().getGenId() + 1;
		} catch (VariableNotFoundException e) {
			dbUtil.writeReadyGenerationInfo(genId, 0);
		}
		for (int i = 0; i < visualTrials.size(); i++) {
			long taskId = globalTimeUtil.currentTimeMicros();
			
			TrainingTrial trial = visualTrials.get(i);
			String spec = trial.toXml();
			System.out.println(spec);
			dbUtil.writeStimObjData(taskId, trial.getGaussSpec().toXml(), trial.getData());
			SaccadeStimSpecSpec stimSpec = new VisualStimSpecSpec(trial.getTargetEyeWinCoords(), trial.getTargetEyeWinSize(), trial.getDuration(), taskId);
			dbUtil.writeStimSpec(taskId, stimSpec.toXml());
			dbUtil.writeTaskToDo(taskId, taskId, -1, genId);
		
		}
		dbUtil.updateReadyGenerationInfo(genId, visualTrials.size());
		System.out.println("Done Generating...");
		return;
		
	}

	public BlockSpec getBlockspec() {
		return blockspec;
	}

	public void setBlockspec(BlockSpec blockspec) {
		this.blockspec = blockspec;
	}

	public Block getBlock() {
		return block;
	}

	public void setBlock(Block block) {
		this.block = block;
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
