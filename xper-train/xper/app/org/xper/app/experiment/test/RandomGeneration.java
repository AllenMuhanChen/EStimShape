package org.xper.app.experiment.test;

import org.xper.Dependency;
import org.xper.exception.VariableNotFoundException;
import org.xper.experiment.StimSpecGenerator;
import org.xper.time.TimeUtil;
import org.xper.util.DbUtil;

public class RandomGeneration {
	@Dependency
	DbUtil dbUtil;
	@Dependency
	TimeUtil globalTimeUtil;
	@Dependency
	StimSpecGenerator generator;
	@Dependency
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
		try {
			genId = dbUtil.readReadyGenerationInfo().getGenId() + 1;
		} catch (VariableNotFoundException e) {
			dbUtil.writeReadyGenerationInfo(genId, 0);
		}
		for (int i = 0; i < taskCount; i++) {
			if (i % 10 == 0) {
				System.out.print(".");
			}
			String spec = generator.generateStimSpec();
			long taskId = globalTimeUtil.currentTimeMicros();
			dbUtil.writeStimSpec(taskId, spec);
			dbUtil.writeTaskToDo(taskId, taskId, -1, genId);
		}
		dbUtil.updateReadyGenerationInfo(genId, taskCount);
		System.out.println("done.");
	}

	public DbUtil getDbUtil() {
		return dbUtil;
	}

	public void setDbUtil(DbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}

	

	public TimeUtil getGlobalTimeUtil() {
		return globalTimeUtil;
	}

	public void setGlobalTimeUtil(TimeUtil globalTimeUtil) {
		this.globalTimeUtil = globalTimeUtil;
	}

	public StimSpecGenerator getGenerator() {
		return generator;
	}

	public void setGenerator(StimSpecGenerator generator) {
		this.generator = generator;
	}
}
