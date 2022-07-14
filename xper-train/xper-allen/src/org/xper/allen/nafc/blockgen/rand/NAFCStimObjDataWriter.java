package org.xper.allen.nafc.blockgen.rand;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.nafc.blockgen.NAFCCoordinates;
import org.xper.allen.nafc.blockgen.NAFCMStickSpecs;
import org.xper.allen.nafc.blockgen.NAFCPaths;
import org.xper.allen.nafc.blockgen.NoisyPngSpecWriter;
import org.xper.allen.nafc.blockgen.StimObjIds;
import org.xper.allen.nafc.blockgen.psychometric.NoisyTrialParameters;
import org.xper.allen.nafc.blockgen.psychometric.Psychometric;
import org.xper.allen.nafc.vo.MStickStimObjData;
import org.xper.allen.specs.NoisyPngSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.drawing.Coordinates2D;

public abstract class NAFCStimObjDataWriter {

	

	public NAFCStimObjDataWriter(int numChoices, Psychometric<String> pngPaths, String noiseMapPath, AllenDbUtil dbUtil,
			Psychometric<AllenMStickSpec> mStickSpecs, NoisyTrialParameters trialParameters, Psychometric<Coordinates2D> coords, Psychometric<Long> stimObjIds) {
		super();
		this.numChoices = numChoices;
		this.pngPaths = pngPaths;
		this.noiseMapPath = noiseMapPath;
		this.dbUtil = dbUtil;
		this.mStickSpecs = mStickSpecs;
		this.trialParameters = trialParameters;
		this.coords = coords;
		this.stimObjIds = stimObjIds;
	}

	protected int numChoices;
	protected Psychometric<String> pngPaths;
	protected String noiseMapPath;
	protected AllenDbUtil dbUtil;
	protected Psychometric<AllenMStickSpec> mStickSpecs = new Psychometric<AllenMStickSpec>();
	protected NoisyTrialParameters trialParameters;
	protected Psychometric<Coordinates2D> coords;
	protected Psychometric<Long> stimObjIds;
	
	
	public void writeStimObjId() {
		writeSampleSpec();
		writeMatchSpec();
		writeDistractorSpecs();
	}

	private void writeSampleSpec() {
		NoisyPngSpecWriter sampleSpecWriter = NoisyPngSpecWriter.createWithNoiseMap(
				coords.getSample(),
				pngPaths.getSample(), noiseMapPath,
				trialParameters.getSize());
	
		sampleSpecWriter.writeSpec();
		NoisyPngSpec sampleSpec = sampleSpecWriter.getSpec();
		
		
		MStickStimObjData sampleMStickObjData = new MStickStimObjData("Sample", mStickSpecs.getSample());
		dbUtil.writeStimObjData(stimObjIds.getSample(), sampleSpec.toXml(), sampleMStickObjData.toXml());
	}

	private void writeMatchSpec() {
		NoisyPngSpecWriter matchSpecWriter = NoisyPngSpecWriter.createWithoutNoiseMap(
				coords.getMatch(),
				pngPaths.getMatch(),
				trialParameters.getSize());
		matchSpecWriter.writeSpec();
		NoisyPngSpec matchSpec = matchSpecWriter.getSpec();
	
		MStickStimObjData matchMStickObjData = new MStickStimObjData("Match", mStickSpecs.getMatch());
		dbUtil.writeStimObjData(stimObjIds.getMatch(), matchSpec.toXml(), matchMStickObjData.toXml());
	}
	
	protected abstract void writeDistractorSpecs();
	
	protected void setStimObjIds(Psychometric<Long> stimObjIds) {
		this.stimObjIds = stimObjIds;
	}

}
