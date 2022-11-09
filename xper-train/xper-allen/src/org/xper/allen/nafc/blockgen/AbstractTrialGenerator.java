package org.xper.allen.nafc.blockgen;



import java.util.Collections;
import java.util.LinkedList;
import java.util.List;
import java.util.stream.IntStream;

import org.xper.Dependency;
import org.xper.allen.util.AllenDbUtil;
import org.xper.exception.VariableNotFoundException;

public abstract class AbstractTrialGenerator {

	@Dependency
	protected AllenDbUtil dbUtil;

	protected Long genId;
	protected List<Trial> trials = new LinkedList<>();

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
		for(Trial trial:trials){
			trial.preWrite();
		}
	}

	protected void shuffleTrials() {
		Collections.shuffle(trials);
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
		for (Trial trial : trials) {
			trial.write();
			Long taskId = trial.getTaskId();
			getDbUtil().writeTaskToDo(taskId, taskId, -1, genId);
		}
	}

	protected void updateReadyGeneration() {
		getDbUtil().updateReadyGenerationInfo(genId, trials.size());
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

	public AllenDbUtil getDbUtil() {
		return dbUtil;
	}

	public void setDbUtil(AllenDbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}
}
