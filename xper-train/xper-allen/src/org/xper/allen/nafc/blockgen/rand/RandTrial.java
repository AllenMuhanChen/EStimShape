package org.xper.allen.nafc.blockgen.rand;

import java.util.List;

import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.nafc.blockgen.NAFCMatchSticks;
import org.xper.allen.nafc.blockgen.NAFCCoordinates;
import org.xper.allen.nafc.blockgen.NAFCPaths;
import org.xper.allen.nafc.blockgen.Trial;
import org.xper.allen.util.AllenDbUtil;

public class RandTrial implements Trial{
	
	//INput Fields
	private AbstractMStickPngTrialGenerator generator;
	private RandNoisyTrialParameters trialParameters;
	


	public RandTrial(AbstractMStickPngTrialGenerator generator, RandNoisyTrialParameters trialParameters) {
		super();
		this.generator = generator;
		this.trialParameters = trialParameters;
	}

	//Private instance fields
	private AllenDbUtil dbUtil;
	private NAFCMatchSticks mSticks = new NAFCMatchSticks();
	private NAFCCoordinates coords;
	private NAFCPaths pngPaths;
	private Long taskId;
	private String noiseMapPath;
	private List<String> noiseMapLabels;
	private StimObjIdsForRandTrial stimObjIds = new StimObjIdsForRandTrial();
	
	
	@Override
	public void preWrite() {

		
	}
	
	@Override
	public void write() {
		assignStimObjIds();
		generateMatchSticks();
		generateNoiseMap();
		assignCoords();
		writeStimObjDataSpecs();
		assignTaskId();
		writeStimSpec();
	}

	private void assignStimObjIds() {
		StimObjIdAssignerForRandTrials stimObjIdAssigner = new StimObjIdAssignerForRandTrials(generator.getGlobalTimeUtil(), trialParameters.getNumDistractors());
		stimObjIdAssigner.getStimObjIds();
		stimObjIds = stimObjIdAssigner.getStimObjIds();
	}
	
	private void generateMatchSticks() {
		MStickGeneratorForRandTrials mStickGenerator = new MStickGeneratorForRandTrials(generator, trialParameters);
		mSticks = mStickGenerator.getNAFCMatchSticks();
	}
	
	@Override
	public Long getTaskId() {
		// TODO Auto-generated method stub
		return null;
	}
}
