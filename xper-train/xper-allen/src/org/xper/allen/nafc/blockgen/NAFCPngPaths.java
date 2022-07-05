package org.xper.allen.nafc.blockgen;

import java.util.List;

public class NAFCPngPaths {
	public String samplePngPath;
	public String matchPngPath;
	public List<String> distractorsPngPaths;

	public NAFCPngPaths(String samplePngPath, String matchPngPath, List<String> distractorsPngPaths) {
		super();
		this.samplePngPath = samplePngPath;
		this.matchPngPath = matchPngPath;
		this.distractorsPngPaths = distractorsPngPaths;
	}

	public NAFCPngPaths() {
		super();
	}

	public String getSamplePngPath() {
		return samplePngPath;
	}


	public String getMatchPngPath() {
		return matchPngPath;
	}


	public List<String> getDistractorsPngPaths() {
		return distractorsPngPaths;
	}

}