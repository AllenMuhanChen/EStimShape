package org.xper.allen.nafc.blockgen.rand;

import java.util.List;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.RandTrialNoiseMapGenerator;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.Stim;
import org.xper.allen.nafc.blockgen.psychometric.NAFCStimSpecWriter;
import org.xper.allen.util.AllenDbUtil;
import org.xper.drawing.Coordinates2D;

public class RandStim implements Stim {

	//INput Fields
	private AbstractMStickPngTrialGenerator generator;
	private RandNoisyTrialParameters trialParameters;

	public RandStim(AbstractMStickPngTrialGenerator generator, RandNoisyTrialParameters trialParameters) {
		super();
		this.generator = generator;
		this.trialParameters = trialParameters;
		this.dbUtil = (AllenDbUtil) generator.getDbUtil();
	}

	//Private instance fields
	private AllenDbUtil dbUtil;
	private Rand<AllenMatchStick> mSticks = new Rand<>();
	private Rand<AllenMStickSpec> mStickSpecs = new Rand<AllenMStickSpec>();
	private Rand<Coordinates2D> coords;
	private Rand<String> experimentPngPaths;
	private Long taskId;
	private String experimentNoiseMapPath;
	private List<String> noiseMapLabels;
	private Rand<Long> stimObjIds = new Rand<Long>();


	@Override
	public void preWrite() {}

	@Override
	public void writeStim() {
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
		stimObjIds = stimObjIdAssigner.getStimObjIds();
	}

	private void generateMatchSticks() {
		MStickGeneratorForRandTrials mStickGenerator = new MStickGeneratorForRandTrials(generator.getMaxImageDimensionDegrees(), trialParameters);
		mSticks = mStickGenerator.getmSticks();
		mStickSpecs = mStickGenerator.getmStickSpecs();
	}

	private void drawPNGs(){
		PNGDrawerForRandTrial drawer = new PNGDrawerForRandTrial(
				generator,
				mSticks,
				stimObjIds
		);
		experimentPngPaths = drawer.getExperimentPngPaths();
	}

	private void generateNoiseMap() {
		RandTrialNoiseMapGenerator noiseMapGenerator = new RandTrialNoiseMapGenerator(stimObjIds.getSample(), mSticks.getSample(), trialParameters.getNoiseParameters(), generator);
		experimentNoiseMapPath = noiseMapGenerator.getExperimentNoiseMapPath();
	}

	private void assignCoords() {
		RandTrialCoordinateAssigner coordAssigner = new RandTrialCoordinateAssigner(
				trialParameters.getSampleDistanceLims(),
				trialParameters.getNumDistractors(),
				trialParameters.getChoiceDistanceLims());

		coords = coordAssigner.getCoords();
	}

	private void writeStimObjDataSpecs() {
		RandTrialStimObjDataWriter stimObjDataWriter = new RandTrialStimObjDataWriter(
				experimentNoiseMapPath,
				dbUtil,
				trialParameters,
				experimentPngPaths,
				stimObjIds,
				mStickSpecs,
				coords
		);
		stimObjDataWriter.writeStimObjId();
	}

	private void assignTaskId() {
		setTaskId(stimObjIds.getSample());
	}

	private void writeStimSpec(){
		NAFCStimSpecWriter stimSpecWriter = new NAFCStimSpecWriter(
				getTaskId(),
				dbUtil,
				trialParameters,
				coords,
				trialParameters.getNumChoices(),
				stimObjIds);

		stimSpecWriter.writeStimSpec();
	}
	@Override
	public Long getTaskId() {
		return taskId;
	}

	public void setTaskId(Long taskId) {
		this.taskId = taskId;
	}
}