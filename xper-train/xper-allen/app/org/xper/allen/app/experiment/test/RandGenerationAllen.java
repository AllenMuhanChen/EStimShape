package org.xper.allen.app.experiment.test;

import org.xper.Dependency;
import org.xper.allen.Block;
import org.xper.allen.config.AllenDbUtil;
import org.xper.allen.experiment.GaussianSpecGenerator;
import org.xper.allen.specs.BlockSpec;
import org.xper.exception.VariableNotFoundException;
import org.xper.experiment.StimSpecGenerator;
import org.xper.time.TimeUtil;
import org.xper.util.DbUtil;

//AC: Removing abstraction with StimSpecGenerator, as random generation heavily depends on what type of stimuli it's using. 
public class RandGenerationAllen {
	@Dependency
	AllenDbUtil dbUtil;
	@Dependency
	TimeUtil globalTimeUtil;
	@Dependency
	GaussianSpecGenerator generator;
	int taskCount;

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
		BlockSpec blockspec = dbUtil.readBlockSpec(blockId);
		Block block = new Block(blockspec);
		char trialList[] = block.generateTrialList();
		//------------
		
		try {
			genId = dbUtil.readReadyGenerationInfo().getGenId() + 1;
		} catch (VariableNotFoundException e) {
			dbUtil.writeReadyGenerationInfo(genId, 0);
		}
		for (int i = 0; i < block.get_taskCount(); i++) {
			if (i % 10 == 0) {
				System.out.print(".");
			}
			//BLOCK LOGIC
			long taskId = globalTimeUtil.currentTimeMicros();
			if (trialList[i]=='c') {
				generator.setSize(0);								//Visual Stimulus
				String spec = generator.generateStimSpec();
				dbUtil.writeStimObjData(taskId, spec, "c");
				generator.reset();
			}
			else if(trialList[i]=='v'){
				
			}
			else if(trialList[i]=='e') {
				generator.setSize(0);								//Visual Stimulus
				String spec = generator.generateStimSpec();
				dbUtil.writeStimObjData(taskId, spec, "c");
				generator.reset();
			}
			else if(trialList[i]=='b') {
				
			}

			dbUtil.writeStimSpec(taskId, spec);
			dbUtil.writeTaskToDo(taskId, taskId, -1, genId);
		}
		dbUtil.updateReadyGenerationInfo(genId, taskCount);
		System.out.println("done.");
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
