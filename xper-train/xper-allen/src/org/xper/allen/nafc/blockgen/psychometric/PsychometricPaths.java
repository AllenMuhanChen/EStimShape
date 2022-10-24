package org.xper.allen.nafc.blockgen.psychometric;

import java.util.LinkedList;
import java.util.List;

import org.xper.allen.nafc.blockgen.NAFCPaths;

public class PsychometricPaths extends NAFCPaths{
	public List<String> psychometricDistractorPaths = new LinkedList<String>();
	public List<String> randDistractorPaths = new LinkedList<String>();
	public PsychometricPaths(String samplePngPath, String matchPngPath, List<String> distractorsPngPaths,
			List<String> psychometricDistractorPaths, List<String> randDistractorPaths) {
		super(samplePngPath, matchPngPath, distractorsPngPaths);
		this.psychometricDistractorPaths = psychometricDistractorPaths;
		this.randDistractorPaths = randDistractorPaths;
	}
	public List<String> getPsychometricDistractorPaths() {
		return psychometricDistractorPaths;
	}
	public void setPsychometricDistractorPaths(List<String> psychometricDistractorPaths) {
		this.psychometricDistractorPaths = psychometricDistractorPaths;
	}
	public List<String> getRandDistractorPaths() {
		return randDistractorPaths;
	}
	public void setRandDistractorPaths(List<String> randDistractorPaths) {
		this.randDistractorPaths = randDistractorPaths;
	}
	
}
