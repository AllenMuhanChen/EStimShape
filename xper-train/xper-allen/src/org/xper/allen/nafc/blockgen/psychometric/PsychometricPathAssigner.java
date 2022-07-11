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
	
	NAFCPaths pngPaths;
	static public PsychometricPathAssigner createWithExistingNAFCPngPathsObj(PsychometricIds psychometricIds, int numPsychometricDistractors, PngBasePaths basePaths, NAFCPaths pngPaths) {
		return new PsychometricPathAssigner(psychometricIds, numPsychometricDistractors, basePaths, pngPaths);
	}
	
	private PsychometricPathAssigner(PsychometricIds psychometricIds, int numPsychometricDistractors, PngBasePaths basePaths) {
		this.psychometricIds = psychometricIds;
		this.numPsychometricDistractors = numPsychometricDistractors;
		this.basePaths = basePaths;
		this.pngPaths = new NAFCPaths();
	}
	
	private PsychometricPathAssigner(PsychometricIds psychometricIds, int numPsychometricDistractors, PngBasePaths basePaths, NAFCPaths pngPaths) {
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
		pngPaths.samplePath = convertPathToExperiment(basePaths.generatorPngPath + "/" + sampleSetId + "_" + sampleStimId + ".png");
		pngPaths.matchPath = pngPaths.samplePath;
		for (int remainingStimId:distractorsStimIds) {
			int index = distractorsStimIds.indexOf(remainingStimId);
			pngPaths.distractorsPaths.add(convertPathToExperiment(basePaths.generatorPngPath + "/" + distractorsSetId+ "_" + remainingStimId + ".png"));
		}
	}
	
	private String convertPathToExperiment(String generatorPath) {
		
		String newPath = generatorPath.replace(basePaths.generatorPngPath, basePaths.experimentPngPath);
	
		return newPath;
	}

	NAFCPaths specPaths = new NAFCPaths();

	private void assignSpecPaths() {
		specPaths.setSamplePath(basePaths.specPath + "/" + sampleSetId + "_" + sampleStimId + "_spec.xml");
		specPaths.setMatchPath(basePaths.specPath + "/" + matchSetId + "_" + matchStimId + "_spec.xml");
		for (Integer stimId : distractorsStimIds) {
			String pathOfDistractorWithStimId = basePaths.specPath + "/" + distractorsSetId + "_" + stimId + "_spec.xml";
			specPaths.getDistractorsPaths().add(pathOfDistractorWithStimId);
		}
	}
	


	public NAFCPaths getPngPaths() {
		return pngPaths;
	}

	public NAFCPaths getSpecPaths() {
		return specPaths;
	}

	public void setSpecPaths(NAFCPaths specPaths) {
		this.specPaths = specPaths;
	}



}
