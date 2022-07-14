package org.xper.allen.nafc.blockgen.psychometric;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

import org.xper.allen.nafc.blockgen.NAFCPaths;
import org.xper.allen.nafc.blockgen.PngBasePaths;

/**
 * Assigns paths for sample, match and distractors given setId and stimId, and number of distractors
 * @author r2_allen
 *
 */
public class PsychometricPathAssigner{


	PsychometricIds psychometricIds;
	int numPsychometricDistractors;
	PngBasePaths basePaths;

	static public PsychometricPathAssigner createWithNewNAFCPngPathsObj(PsychometricIds psychometricIds, int numPsychometricDistractors, PngBasePaths basePaths) {
		return new PsychometricPathAssigner(psychometricIds, numPsychometricDistractors, basePaths);
	}
	
	Psychometric<String> pngPaths;
	static public PsychometricPathAssigner createWithExistingNAFCPngPathsObj(PsychometricIds psychometricIds, int numPsychometricDistractors, PngBasePaths basePaths, Psychometric<String> pngPaths) {
		return new PsychometricPathAssigner(psychometricIds, numPsychometricDistractors, basePaths, pngPaths);
	}
	
	private PsychometricPathAssigner(PsychometricIds psychometricIds, int numPsychometricDistractors, PngBasePaths basePaths) {
		this.psychometricIds = psychometricIds;
		this.numPsychometricDistractors = numPsychometricDistractors;
		this.basePaths = basePaths;
		this.pngPaths = new Psychometric<String>();
	}
	
	private PsychometricPathAssigner(PsychometricIds psychometricIds, int numPsychometricDistractors, PngBasePaths basePaths, Psychometric<String> pngPaths) {
		this.psychometricIds = psychometricIds;
		this.numPsychometricDistractors = numPsychometricDistractors;
		this.basePaths = basePaths;
		this.pngPaths = pngPaths;
	}


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
		pngPaths.setSample(convertPathToExperiment(basePaths.generatorPngPath + "/" + sampleSetId + "_" + sampleStimId + ".png"));
		pngPaths.setMatch(pngPaths.getSample());
		for (int remainingStimId:distractorsStimIds) {
			int index = distractorsStimIds.indexOf(remainingStimId);
			pngPaths.addPsychometricDistractor(convertPathToExperiment(basePaths.generatorPngPath + "/" + distractorsSetId+ "_" + remainingStimId + ".png"));
		}
	}
	
	private String convertPathToExperiment(String generatorPath) {
		
		String newPath = generatorPath.replace(basePaths.generatorPngPath, basePaths.experimentPngPath);
	
		return newPath;
	}

	Psychometric<String> specPaths = new Psychometric<String>();

	private void assignSpecPaths() {
		specPaths.setSample(basePaths.specPath + "/" + sampleSetId + "_" + sampleStimId + "_spec.xml");
		specPaths.setMatch(basePaths.specPath + "/" + matchSetId + "_" + matchStimId + "_spec.xml");
		for (Integer stimId : distractorsStimIds) {
			String pathOfDistractorWithStimId = basePaths.specPath + "/" + distractorsSetId + "_" + stimId + "_spec.xml";
			specPaths.addPsychometricDistractor(pathOfDistractorWithStimId);
		}
	}
	

	public Psychometric<String> getPngPaths() {
		return pngPaths;
	}

	public Psychometric<String> getSpecPaths() {
		return specPaths;
	}




}
