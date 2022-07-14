package org.xper.allen.nafc.blockgen.rand;

import java.util.List;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.RandTrialNoiseMapGenerator;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.nafc.blockgen.NAFCCoordinateAssigner;
import org.xper.allen.nafc.blockgen.NAFCCoordinates;
import org.xper.allen.nafc.blockgen.NAFCPaths;
import org.xper.allen.nafc.blockgen.Trial;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricCoordinateAssigner;
import org.xper.allen.nafc.blockgen.psychometric.Psychometric;
import org.xper.allen.util.AllenDbUtil;
import org.xper.drawing.Coordinates2D;

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
	private Psychometric<AllenMatchStick> mSticks = new Psychometric<AllenMatchStick>();
	private Psychometric<AllenMStickSpec> mStickSpecs = new Psychometric<AllenMStickSpec>();
	private Psychometric<Coordinates2D> coords;
	private Psychometric<String> pngPaths;
	private Long taskId;
	private String noiseMapPath;
	private List<String> noiseMapLabels;
	private Psychometric<Long> stimObjIds = new Psychometric<Long>();
	
	
	@Override
	public void preWrite() {

		
	}
	
	@Override
	public void write() {
		assignStimObjIds();
		generateMatchSticks();
		drawPNGs();
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
		mSticks = mStickGenerator.getNAFCMSticks();
		mStickSpecs = mStickGenerator.getNAFCMStickSpecs();
	}
	
	private void generateNoiseMap() {
		RandTrialNoiseMapGenerator noiseMapGenerator = new RandTrialNoiseMapGenerator(stimObjIds.getSampleId(), mSticks.getSampleMStick(), trialParameters.getNoiseParameters(), generator);
		noiseMapGenerator.getNoiseMapPath();
	}
	
	private void assignCoords() {
		NAFCCoordinateAssigner coordAssigner = new PsychometricCoordinateAssigner(
				trialParameters.getSampleDistanceLims(),
				trialParameters.getNumChoices());
		

		coords = coordAssigner.getCoords();
	}
	
	private void writeStimObjDataSpecs() {
		RandTrialStimObjDataWriter stimObjDataWriter = new RandTrialStimObjDataWriter(
				trialParameters.getNumChoices(),
				pngPaths,
				noiseMapPath,
				dbUtil,
				mStickSpecs,
				trialParameters,
				coords,
				stimObjIds);
		stimObjDataWriter.writeStimObjId();
	}
	
	private void assignTaskId() {
		setTaskId(stimObjIds.getSampleId());
	}
	
	@Override
	public Long getTaskId() {
		// TODO Auto-generated method stub
		return null;
	}
	
	public void setTaskId(Long taskId) {
		this.taskId = taskId;
	}
}
