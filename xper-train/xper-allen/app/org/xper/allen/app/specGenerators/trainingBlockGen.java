package org.xper.allen.app.specGenerators;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Random;

import org.xper.Dependency;
import org.xper.allen.Block;
import org.xper.allen.app.blockGenerators.VisualTrial;
import org.xper.allen.app.blockGenerators.trials.Trial;
import org.xper.allen.app.blockGenerators.trials.bothTrial;
import org.xper.allen.app.blockGenerators.trials.catchTrial;
import org.xper.allen.app.blockGenerators.trials.estimTrial;
import org.xper.allen.app.blockGenerators.trials.visualTrial;
import org.xper.allen.specs.BlockSpec;
import org.xper.allen.specs.GaussSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.allen.util.AllenXMLUtil;
import org.xper.exception.VariableNotFoundException;
import org.xper.time.TimeUtil;

public class trainingBlockGen {
	@Dependency
	AllenDbUtil dbUtil;
	@Dependency
	TimeUtil globalTimeUtil;
	@Dependency
	AllenXMLUtil xmlUtil;
	
	int[] channel_list = {1};
	int num_per_chan;
	long blockId;
	Trial[] trialList;
	BlockSpec blockspec;
	Block block;
	char[] trialTypeList;
	/**
	 * Selects visual stimuli randomly from stimTypes
	 */
	Random r = new Random();
	
	public trainingBlockGen() {
	}
	
	
	long genId = 1;
	public Trial[] generate(String filepath, double targetEyeWinSize) { //
	
		ArrayList<GaussSpec> gaussSpecs = (ArrayList<GaussSpec>) xmlUtil.parseFile(filepath);
		System.out.println(gaussSpecs.size());
		try {
			genId = dbUtil.readReadyGenerationInfo().getGenId() + 1;
		} catch (VariableNotFoundException e) {
			dbUtil.writeReadyGenerationInfo(genId, 0);
		}
		for (int i = 0; i < gaussSpecs.size(); i++) {
			long taskId = globalTimeUtil.currentTimeMicros();
			
			VisualTrial trial = new VisualTrial(gaussSpecs.get(i), targetEyeWinSize);
			String spec = trial.toXml();
			System.out.println(spec);
			dbUtil.writeStimObjData(taskId, gaussSpecs.get(i).toXml(), "");
			visualTrial vistrial = new visualTrial(new long[] {taskId}, targetEyeWinSize);
			dbUtil.writeStimSpec(taskId, vistrial.toXml());
			dbUtil.writeTaskToDo(taskId, taskId, -1, genId);
		}
		dbUtil.updateReadyGenerationInfo(genId, gaussSpecs.size());
		System.out.println("Done Generating...");
		return trialList;
		
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
