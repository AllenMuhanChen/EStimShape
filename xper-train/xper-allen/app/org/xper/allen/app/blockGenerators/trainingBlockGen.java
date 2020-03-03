package org.xper.allen.app.blockGenerators;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Random;

import org.xper.Dependency;
import org.xper.allen.Block;
import org.xper.allen.app.blockGenerators.trials.Trial;
import org.xper.allen.app.blockGenerators.trials.bothTrial;
import org.xper.allen.app.blockGenerators.trials.catchTrial;
import org.xper.allen.app.blockGenerators.trials.estimTrial;
import org.xper.allen.app.blockGenerators.trials.visualTrial;
import org.xper.allen.config.AllenDbUtil;
import org.xper.allen.specs.BlockSpec;
import org.xper.exception.VariableNotFoundException;
import org.xper.time.TimeUtil;

public class trainingBlockGen {
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
	/**
	 * Selects visual stimuli randomly from stimTypes
	 */
	Random r = new Random();
	
	public trainingBlockGen() {
	}
	
	
	long genId = 1;
	public Trial[] generate(int blockId, ArrayList<Integer> visualTypes) { //
		BlockSpec blockspec = dbUtil.readBlockSpec(blockId);
		Block block = new Block(blockspec);
		char[] trialTypeList = block.generateTrialList();
		System.out.println(trialTypeList);
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
				int randIndex;
				try {
					randIndex = r.nextInt(visualTypes.size());
				}catch(Exception e) {
					randIndex = 0;
				}
				long[] stims = {visualTypes.get(randIndex)};
				trialList[i] = new visualTrial(stims); 
			}
			else if (trialTypeList[i]=='e') {
				System.out.println("NON CATCH OR VISUAL STIMULUS DETECTED. CHANGE BLOCKID.");
			}
			else if (trialTypeList[i]=='b') {
				System.out.println("NON CATCH OR VISUAL STIMULUS DETECTED. CHANGE BLOCKID.");
			}
			String spec = trialList[i].toXml();
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
