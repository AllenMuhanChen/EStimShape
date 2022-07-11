package org.xper.allen.nafc.blockgen;

import java.util.ArrayList;
import java.util.List;

public class NAFCPaths {
	public String samplePath;
	public String matchPath;
	public List<String> distractorsPaths = new ArrayList<String>();

	public NAFCPaths(String samplePngPath, String matchPngPath, List<String> distractorsPngPaths) {
		super();
		this.samplePath = samplePngPath;
		this.matchPath = matchPngPath;
		this.distractorsPaths = distractorsPngPaths;
	}

	public NAFCPaths() {
		super();
	}
	
	public void addToDistractors(List<String> pathsToAdd) {
		this.distractorsPaths.addAll(pathsToAdd);
	}
	
	public void addToDistractors(String pathToAdd) {
		this.distractorsPaths.add(pathToAdd);
	}

	public String getSamplePath() {
		return samplePath;
	}


	public String getMatchPath() {
		return matchPath;
	}


	public List<String> getDistractorsPaths() {
		return distractorsPaths;
	}

	public void setSamplePath(String samplePath) {
		this.samplePath = samplePath;
	}

	public void setMatchPath(String matchPath) {
		this.matchPath = matchPath;
	}

	public void setDistractorsPaths(List<String> distractorsPaths) {
		this.distractorsPaths = distractorsPaths;
	}
	

	

}