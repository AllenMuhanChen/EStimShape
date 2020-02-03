package org.xper.allen.app.experiment.test;

import org.xper.Dependency;
import org.xper.allen.Block;
import org.xper.allen.app.blockGenerators.sampleBlockGen;
import org.xper.allen.app.blockGenerators.trials.Trial;
import org.xper.allen.app.blockGenerators.trials.trial;
import org.xper.allen.config.AllenDbUtil;
import org.xper.allen.experiment.EStimObjDataGenerator;
import org.xper.allen.experiment.GaussianSpecGenerator;
import org.xper.allen.specs.BlockSpec;
import org.xper.exception.VariableNotFoundException;
import org.xper.time.TimeUtil;


//AC: Removing abstraction with StimSpecGenerator, as random generation heavily depends on what type of stimuli it's using. 
public class RandGenerationAllen {
	@Dependency
	AllenDbUtil dbUtil;
	@Dependency
	TimeUtil globalTimeUtil;
	@Dependency
	GaussianSpecGenerator generator;
	@Dependency
	EStimObjDataGenerator egenerator;
	int taskCount;
	
	Trial[] trialList;

	public int getTaskCount() {
		return taskCount;
	}

	public void setTaskCount(int taskCount) {
		this.taskCount = taskCount;
	}
	
	public void generate() {
		System.out.print("Generating ");
		long genId = 1;
		//BLOCK LOGIC
		long blockId = genId;
		sampleBlockGen blockgen = new sampleBlockGen(blockId);
		trialList = blockgen.generate();
		Block block = blockgen.getBlock();
		//------------
		
		try {
			genId = dbUtil.readReadyGenerationInfo().getGenId() + 1;
		} catch (VariableNotFoundException e) {
			dbUtil.writeReadyGenerationInfo(genId, 0);
		}
		
		for (int i=0; i < block.get_taskCount(); i++) {
			long taskId = globalTimeUtil.currentTimeMicros();
			
			
			dbUtil.writeStimSpec(taskId, trialList[i].getEStimObjData().toXml());
		}
		
		//dbUtil.writeStimSpec(taskId, blockgen.toXml());
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

	public GaussianSpecGenerator getGenerator() {
		return generator;
	}

	public void setGenerator(GaussianSpecGenerator generator) {
		this.generator = generator;
	}
	
}
