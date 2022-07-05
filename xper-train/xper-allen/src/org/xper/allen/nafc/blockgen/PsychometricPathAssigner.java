package org.xper.allen.nafc.blockgen;

import java.util.ArrayList;
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
	PngBasePaths basePaths;

	static public PsychometricPathAssigner createWithNewNAFCPngPathsObj(PsychometricIds psychometricIds, int numPsychometricDistractors, PngBasePaths basePaths) {
		return new PsychometricPathAssigner(psychometricIds, numPsychometricDistractors, basePaths);
	}
	
	NAFCPngPaths pngPaths;
	static public PsychometricPathAssigner createWithExistingNAFCPngPathsObj(PsychometricIds psychometricIds, int numPsychometricDistractors, PngBasePaths basePaths, NAFCPngPaths pngPaths) {
		return new PsychometricPathAssigner(psychometricIds, numPsychometricDistractors, basePaths, pngPaths);
	}
	
	private PsychometricPathAssigner(PsychometricIds psychometricIds, int numPsychometricDistractors, PngBasePaths basePaths) {
		this.psychometricIds = psychometricIds;
		this.numPsychometricDistractors = numPsychometricDistractors;
		this.basePaths = basePaths;
		this.pngPaths = new NAFCPngPaths();
	}
	
	private PsychometricPathAssigner(PsychometricIds psychometricIds, int numPsychometricDistractors, PngBasePaths basePaths, NAFCPngPaths pngPaths) {
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
		pngPaths.samplePngPath = convertPathToExperiment(basePaths.generatorPngPath + "/" + sampleSetId + "_" + sampleStimId + ".png");
		pngPaths.matchPngPath = pngPaths.samplePngPath;
		for (int remainingStimId:distractorsStimIds) {
			int index = distractorsStimIds.indexOf(remainingStimId);
			pngPaths.distractorsPngPaths.add(convertPathToExperiment(basePaths.generatorPngPath + "/" + distractorsSetId+ "_" + remainingStimId + ".png"));
		}
	}
	
	private String convertPathToExperiment(String generatorPath) {
		
		String newPath = generatorPath.replace(basePaths.generatorPngPath, basePaths.experimentPngPath);
	
		return newPath;
	}

	String sampleSpecPath;
	String matchSpecPath;
	List<String> distractorsSpecPaths = new LinkedList<String>();
	
	private void assignSpecPaths() {
		sampleSpecPath = basePaths.specPath + "/" + sampleSetId + "_" + sampleStimId + "_spec.xml";
		matchSpecPath = basePaths.specPath + "/" + matchSetId + "_" + matchStimId + "_spec.xml";
		for (Integer stimId : distractorsStimIds) {
			String pathOfDistractorWithStimId = basePaths.specPath + "/" + distractorsSetId + "_" + stimId + "_spec.xml";
			distractorsSpecPaths.add(pathOfDistractorWithStimId);
		}
	}
	
	public String getSamplePngPath() {
		return pngPaths.samplePngPath;
	}

	public String getMatchPngPath() {
		return pngPaths.matchPngPath;
	}

	public List<String> getDistractorsPngPaths() {
		return pngPaths.distractorsPngPaths;
	}


	public String getGeneratorPngPath() {
		return basePaths.generatorPngPath;
	}


	public String getSpecPath() {
		return sampleSpecPath;
	}


	public String getMatchSpecPath() {
		return matchSpecPath;
	}


	public List<String> getDistractorsSpecPaths() {
		return distractorsSpecPaths;
	}


	public String getSampleSpecPath() {
		return sampleSpecPath;
	}


	public NAFCPngPaths getPngPaths() {
		return pngPaths;
	}



}
