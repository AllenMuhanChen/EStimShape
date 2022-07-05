package org.xper.allen.nafc.blockgen;

import java.util.LinkedList;
import java.util.List;

import org.xper.allen.nafc.vo.NoiseType;
import org.xper.allen.util.AllenDbUtil;

public class RandNoisyMStickPngTrial extends NAFCTrialWriter{
	private AbstractMStickPngTrialGenerator gen;
	private AllenDbUtil dbUtil;
	
	//Parameter Fields
	int numQMDistractors;
	int numRandDistractors;
	int numQMCategories;
	NoiseType noiseType;
	double[] noiseChance;
	
	//Helper Fields
	int numDistractors;
	
	//Fields that are written to the Db
	Long sampleId;
	String samplePngPath;
	String noiseMapPath;
	List<String> noiseMapLabels;
	Long matchId;
	String matchPngPath;
	List<Long> distractorsIds = new LinkedList<Long>();
	List<Long> qmDistractorIds = new LinkedList<Long>();
	List<Long> randDistractorIds = new LinkedList<Long>();

	//TrialGenData
	NoisyMStickNAFCRandTrialGenData genData;
	
	public RandNoisyMStickPngTrial(AbstractMStickPngTrialGenerator gen, NoisyMStickNAFCRandTrialGenData trialGenData) {
		super();
		this.gen = gen;
		this.dbUtil = gen.getDbUtil();
		this.genData = trialGenData;
	}
	
	
	
	@Override
	public Long write() {
		
		
		return null;
	}

}
