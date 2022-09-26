package org.xper.mockxper;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicBoolean;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.db.vo.GenerationInfo;
import org.xper.db.vo.GenerationTaskToDoList;
import org.xper.db.vo.TaskSpikeRate;
import org.xper.db.vo.TaskToDoEntry;
import org.xper.exception.MockAcqDataIOException;
import org.xper.experiment.Stoppable;
import org.xper.time.TimeUtil;
import org.xper.util.DbUtil;

/**
 * Master entry point for using the MockXper tool.
 * 
 * @author wang
 * 
 */
public class MockXper implements Stoppable {
	static Logger logger = Logger.getLogger(MockXper.class);

	AtomicBoolean done = new AtomicBoolean(false);
	CountDownLatch finished = null;
	long taskDoneMaxId;
	MockGeneration gen;
	GenerationInfo curGenDef;
	
	@Dependency
	TaskAcqDataBuilder acqDataBuilder;
	@Dependency
	TimeUtil globalTimeUtil;
	@Dependency
	DbUtil dbUtil;
	@Dependency
	MockSpikeGenerator spikeGen;
	@Dependency
	int batchSize;
	@Dependency
	GenerationManager generationManager;

	public MockXper() {
		curGenDef = new GenerationInfo();
		curGenDef.setGenId(-1);
	}

	public void stop() {
		System.out.print("Stopping MockXper ...");
		this.done.set(true);
		try {
			finished.await();
		} catch (InterruptedException e) {
			logger.warn(e.toString());
		}
	}

	public MockGeneration getNewGeneration() {
		MockGeneration newGen = generationManager.getCurrentGenerationInDb();
		if (newGen.getGenDef().getGenId() <= curGenDef.getGenId()) {
			return null;
		} else {
			curGenDef = newGen.getGenDef();
			return newGen;
		}
	}

	/**
	 * Run the generation, mock spike rate for each task. It populates TaskDone,
	 * AcqSession and AcqData tables appropriately.
	 * 
	 * @param taskSpikeRate
	 *            List of {@link TaskSpikeRate} of all the tasks to run.
	 * 
	 * 
	 */
	public void mockRun(List<TaskSpikeRate> taskSpikeRate) {
		if (taskSpikeRate.isEmpty()) {
			logger.info("No task to do.");
			return;
		}
		long startTime = globalTimeUtil.currentTimeMicros();
		long stopTime = Long.MAX_VALUE;

		try {
			ByteArrayOutputStream out = new ByteArrayOutputStream();
			System.out.println("   Begin AcqSession: " + startTime);
			dbUtil.writeBeginAcqSession(startTime);
			acqDataBuilder.sessionInit();
			for (TaskSpikeRate ts : taskSpikeRate) {
				System.out.println("      Task: " + ts.getTaskId());
				byte[] data = acqDataBuilder.buildAcqData(ts);
				out.write(data);
				long tstamp = globalTimeUtil.currentTimeMicros();
				dbUtil.writeTaskDone(tstamp, ts.getTaskId(), 0);
			}
			dbUtil.writeAcqData(globalTimeUtil.currentTimeMicros(), out
					.toByteArray());
		} catch (RuntimeException e) {
			e.printStackTrace();
			throw e;
		} catch (IOException e) {
			throw new MockAcqDataIOException(e);
		} finally {
			try {
				stopTime = globalTimeUtil.currentTimeMicros();
				dbUtil.writeEndAcqSession(startTime, stopTime);
				System.out.println("   End AcqSession: " + stopTime);
			} catch (Exception e) {
				logger.warn(e.getMessage());
				e.printStackTrace();
			}
		}
	}

	/**
	 * Run the current generation <code>batchSize</code> tasks at a time.
	 * 
	 */

	protected void runCurrentGeneration() {
		long batchTaskDoneMaxId = taskDoneMaxId;
		ArrayList<TaskSpikeRate> spike = new ArrayList<TaskSpikeRate>();
		GenerationTaskToDoList tasks = gen.getTaskToDoList();
		System.out.println("GenerationTaskList -> genId " + tasks.getGenId()
				+ " size " + tasks.getTasks().size());
		int batchCount = 0;
		for (TaskToDoEntry taskDef : tasks.getTasks()) {
			if (taskDoneMaxId < taskDef.getTaskId()) {
				TaskSpikeRate t = new TaskSpikeRate();
				t.setTaskId(taskDef.getTaskId());
				t.setSpikeRate(spikeGen.getSpikeRate(t.getTaskId()));
				spike.add(t);
				batchCount++;
				batchTaskDoneMaxId = t.getTaskId();
			}
			if (batchCount == batchSize) {
				mockRun(spike);
				if (done.get())
					return;
				taskDoneMaxId = batchTaskDoneMaxId;
				spike.clear();
				batchCount = 0;
				// Return as soon as the new generation is ready
				MockGeneration newGen = getNewGeneration();
				if (newGen != null) {
					gen = newGen;
					return;
				}
			}
		}
		// Last generation, task count possibly less than batchSize
		if (batchCount > 0) {
			mockRun(spike);
			taskDoneMaxId = batchTaskDoneMaxId;
			spike.clear();
			batchCount = 0;
		}
		gen = getNewGeneration();
	}

	public void run() {
		try {
			done.set(false);
			finished = new CountDownLatch(1);

			gen = getNewGeneration();
			if (gen != null) {
				taskDoneMaxId = dbUtil.readTaskDoneCompleteMaxId();
				while (!done.get()) {
					if (gen != null) {
						runCurrentGeneration();
					} else {
						try {
							Thread.sleep(1000);
						} catch (InterruptedException e) {
						}
						gen = getNewGeneration();
					}
				}
			} else {
				System.out.println("No generation ready.");
			}
		} finally {
			try {
				System.out.println("done.");
				finished.countDown();
			} catch (Exception e) {
				logger.warn(e.getMessage());
				e.printStackTrace();
			}
		}
	}

	public void setSpikeGen(MockSpikeGenerator spikeGen) {
		this.spikeGen = spikeGen;
	}

	public void setBatchSize(int batchSize) {
		this.batchSize = batchSize;
	}

	public void setDbUtil(DbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}

	public void setAcqDataBuilder(TaskAcqDataBuilder acqDataBuilder) {
		this.acqDataBuilder = acqDataBuilder;
	}

	public GenerationManager getGenerationManager() {
		return generationManager;
	}

	public void setGenerationManager(GenerationManager generationManager) {
		this.generationManager = generationManager;
	}

	public TimeUtil getGlobalTimeUtil() {
		return globalTimeUtil;
	}

	public void setGlobalTimeUtil(TimeUtil globalTimeUtil) {
		this.globalTimeUtil = globalTimeUtil;
	}
	
	
}