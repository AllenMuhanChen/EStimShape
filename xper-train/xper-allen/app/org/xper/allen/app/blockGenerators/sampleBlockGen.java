package org.xper.allen.app.blockGenerators;

import java.util.Arrays;

import org.xper.Dependency;
import org.xper.allen.Block;
import org.xper.allen.app.blockGenerators.trials.*;
import org.xper.allen.config.AllenDbUtil;
import org.xper.allen.specs.BlockSpec;
import org.xper.time.TimeUtil;

import com.thoughtworks.xstream.XStream;

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
	
	public Trial[] generate(long blockId) { //
		BlockSpec blockspec = dbUtil.readBlockSpec(blockId);
		Block block = new Block(blockspec);
		char[] trialTypeList = block.generateTrialList();
		trialList = new Trial[block.get_taskCount()];
		
		for (int i = 0; i < block.get_taskCount(); i++) {
			long taskId = globalTimeUtil.currentTimeMicros();
			
			if (trialTypeList[i]=='c') {
				trialList[i] = new catchTrial();
			}
			else if (trialTypeList[i]=='v') {
				trialList[i] = new visualTrial(); 
			}
			else if (trialTypeList[i]=='e') {
				trialList[i] = new estimTrial();
			}
			else if (trialTypeList[i]=='b') {
				trialList[i] = new bothTrial();
			}
			String spec = trialList[i].toXml();
			dbUtil.writeStimSpec(taskId, spec);
		}
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
