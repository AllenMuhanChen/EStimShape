package org.xper.allen.app.blockGenerators;

import java.util.Arrays;

import org.xper.Dependency;
import org.xper.allen.Block;
import org.xper.allen.app.blockGenerators.trials.*;
import org.xper.allen.config.AllenDbUtil;
import org.xper.allen.specs.BlockSpec;
import org.xper.exception.VariableNotFoundException;
import org.xper.time.TimeUtil;


public class sampleBlockGen {

	@Dependency
	AllenDbUtil dbUtil;
	@Dependency
	TimeUtil globalTimeUtil;
	
	int[] channel_list = {1};
	int num_per_chan;
	long blockId;
	Trial[] trialList;
	BlockSpec blockspec;
	Block block;
	char[] trialTypeList;
	public sampleBlockGen() {
		
	}
	long genId = 1;
	public Trial[] generate(long blockId) { //
		blockId = 3;
		BlockSpec blockspec = dbUtil.readBlockSpec(blockId);
		Block block = new Block(blockspec);
		char[] trialTypeList = block.generateTrialList();
		trialList = new Trial[block.get_taskCount()];
		try {
			genId = dbUtil.readReadyGenerationInfo().getGenId() + 1;
		} catch (VariableNotFoundException e) {
			dbUtil.writeReadyGenerationInfo(genId, 0);
		}
		for (int i = 0; i < block.get_taskCount(); i++) {
			long taskId = globalTimeUtil.currentTimeMicros();
			
			if (trialTypeList[i]=='c') {
				trialList[i] = new catchTrial();
			}
			else if (trialTypeList[i]=='v') {
				long[] stims = {1,2,3};
				trialList[i] = new visualTrial(stims); 
			}
			else if (trialTypeList[i]=='e') {
				long[] stims = {1,2,3};
				int[] chans = {1,2,3};
				trialList[i] = new estimTrial(stims, chans);
			}
			else if (trialTypeList[i]=='b') {
				trialList[i] = new bothTrial();
			}
			String spec = Trial.toXml(trialList[i]);
			dbUtil.writeStimSpec(taskId, spec);
			dbUtil.writeTaskToDo(taskId, taskId, -1, genId);
		}
		dbUtil.updateReadyGenerationInfo(genId, block.get_taskCount());
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

}
