package org.xper.allen.nafc.blockgen;



import java.util.Collections;
import java.util.LinkedList;
import java.util.List;
import java.util.stream.IntStream;

import org.xper.Dependency;
import org.xper.allen.util.AllenDbUtil;
import org.xper.exception.VariableNotFoundException;
import org.xper.allen.Stim;
import org.xper.time.TimeUtil;
import org.xper.util.DbUtil;

public abstract class AbstractTrialGenerator<T extends Stim> implements TrialGenerator {

	@Dependency
	protected DbUtil dbUtil;
	@Dependency
	protected TimeUtil globalTimeUtil;

	protected Long genId;
	protected List<T> stims = new LinkedList<>();

	@Override
	public void generate(){
		init();
		addTrials();
		preWriteTrials();
		shuffleTrials();
		updateGenId();
		writeTrials();
		updateReadyGeneration();
		tearDown();
	}

	protected void init(){}
	protected abstract void addTrials();

	protected void preWriteTrials() {
		for(Stim stim : getStims()){
			stim.preWrite();
		}
	}

	protected void shuffleTrials() {
		Collections.shuffle(getStims());
	}

	protected void updateGenId() {
		try {
			/*
			  Gen ID is important for xper to be able to load new tasks on the fly. It will only do so if the generation Id is upticked.
			 */
			genId = getDbUtil().readReadyGenerationInfo().getGenId() + 1;
		} catch (VariableNotFoundException e) {
			getDbUtil().writeReadyGenerationInfo(0, 0);
		}
	}

	protected void writeTrials() {
		for (Stim stim : getStims()) {
			stim.writeStim();
			Long taskId = stim.getTaskId();
			getDbUtil().writeTaskToDo(taskId, taskId, -1, genId);
		}
	}

	protected void updateReadyGeneration() {
		getDbUtil().updateReadyGenerationInfo(genId, getStims().size());
		System.out.println("Done Generating...");
	}

	protected void tearDown(){}

	protected static int[] frequencyToNumTrials(double[] typesFrequencies, int numTrials) {
		int[] typesNumTrials = new int[typesFrequencies.length];
		for(int i=0; i<typesFrequencies.length; i++) {
			typesNumTrials[i] = (int) Math.round((double) numTrials * typesFrequencies[i]);
		}
		if(IntStream.of(typesNumTrials).sum()!= numTrials) {
			throw new IllegalArgumentException("Total Round(numTrials .* Frequencies) should = numTrials");
		}
		return typesNumTrials;
	}

	public DbUtil getDbUtil() {
		return dbUtil;
	}

	public void setDbUtil(DbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}

	public List<T> getStims() {
		return stims;
	}

	public void setStims(List<T> stims) {
		this.stims = stims;
	}

	public TimeUtil getGlobalTimeUtil() {
		return globalTimeUtil;
	}

	public void setGlobalTimeUtil(TimeUtil globalTimeUtil) {
		this.globalTimeUtil = globalTimeUtil;
	}
}