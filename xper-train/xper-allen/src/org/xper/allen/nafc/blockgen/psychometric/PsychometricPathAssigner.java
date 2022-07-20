package org.xper.allen.nafc.blockgen.psychometric;

import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

/**
 * Assigns paths for sample, match and distractors given setId and stimId, and number of distractors
 * @author r2_allen
 *
 */
public class PsychometricPathAssigner{
	PsychometricIds psychometricIds;
	int numPsychometricDistractors;
	AbstractPsychometricTrialGenerator generator;

	public PsychometricPathAssigner(PsychometricIds psychometricIds, int numPsychometricDistractors, AbstractPsychometricTrialGenerator generator) {
		this.psychometricIds = psychometricIds;
		this.numPsychometricDistractors = numPsychometricDistractors;
		this.generator = generator;
	}

	Psychometric<String> experimentPngPaths = new Psychometric<>();



	public void assign() {
		assignSetAndStimIdsToStimuli();
		assignPngPaths();
		assignSpecPaths();
	}


	long sampleSetId;
	int sampleStimId;
	private long matchSetId;
	private long matchStimId;
	private long distractorsSetId;
	private List<Integer> distractorsStimIds;
	

	private void assignSetAndStimIdsToStimuli() {
		sampleSetId = psychometricIds.setId;
		sampleStimId = psychometricIds.stimId;
		matchSetId = sampleSetId;
		matchStimId = sampleStimId;
		distractorsSetId = psychometricIds.setId;
		List<Integer> stimIdsRemaining = new LinkedList<>(psychometricIds.allStimIds);
		stimIdsRemaining.remove(psychometricIds.allStimIds.indexOf(psychometricIds.stimId));
		Collections.shuffle(stimIdsRemaining);
		distractorsStimIds = stimIdsRemaining.subList(0, numPsychometricDistractors);		
	}
	
	

	private void assignPngPaths() {
		experimentPngPaths.setSample(generator.experimentPsychometricPngPath + "/" + sampleSetId + "_" + sampleStimId + ".png");
		experimentPngPaths.setMatch(experimentPngPaths.getSample());
		for (int remainingStimId:distractorsStimIds) {
			experimentPngPaths.addPsychometricDistractor(generator.experimentPsychometricPngPath + "/" + distractorsSetId+ "_" + remainingStimId + ".png");
		}
	}

	Psychometric<String> specPaths = new Psychometric<String>();

	private void assignSpecPaths() {
		specPaths.setSample(generator.getGeneratorPsychometricSpecPath() + "/" + sampleSetId + "_" + sampleStimId + "_spec.xml");
		specPaths.setMatch(generator.getGeneratorPsychometricSpecPath() + "/" + matchSetId + "_" + matchStimId + "_spec.xml");
		for (Integer stimId : distractorsStimIds) {
			String pathOfDistractorWithStimId = generator.getGeneratorPsychometricSpecPath() + "/" + distractorsSetId + "_" + stimId + "_spec.xml";
			specPaths.addPsychometricDistractor(pathOfDistractorWithStimId);
		}
	}
	

	public Psychometric<String> getExperimentPngPaths() {
		return experimentPngPaths;
	}

	public Psychometric<String> getSpecPaths() {
		return specPaths;
	}




}
