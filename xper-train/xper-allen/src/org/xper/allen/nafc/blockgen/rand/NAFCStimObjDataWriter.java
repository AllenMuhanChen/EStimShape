package org.xper.allen.nafc.blockgen.rand;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.nafc.blockgen.*;
import org.xper.allen.nafc.blockgen.psychometric.NoisyTrialParameters;
import org.xper.allen.nafc.blockgen.psychometric.Psychometric;
import org.xper.allen.nafc.vo.MStickStimObjData;
import org.xper.allen.specs.NoisyPngSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.drawing.Coordinates2D;

public abstract class NAFCStimObjDataWriter {

	protected String noiseMapPath;
	protected AllenDbUtil dbUtil;
	protected NoisyTrialParameters trialParameters;

	public NAFCStimObjDataWriter(String noiseMapPath, AllenDbUtil dbUtil, NoisyTrialParameters trialParameters) {
		this.noiseMapPath = noiseMapPath;
		this.dbUtil = dbUtil;
		this.trialParameters = trialParameters;
	}

	public void writeStimObjId() {
		writeSampleSpec();
		writeMatchSpec();
		writeDistractorSpecs();
	}

	private void writeSampleSpec() {
		NoisyPngSpecWriter sampleSpecWriter = NoisyPngSpecWriter.createWithNoiseMap(
				getCoords().getSample(),
				getPngPaths().getSample(), noiseMapPath,
				trialParameters.getSize());
	
		sampleSpecWriter.writeSpec();
		NoisyPngSpec sampleSpec = sampleSpecWriter.getSpec();
		
		
		MStickStimObjData sampleMStickObjData = new MStickStimObjData("sample", getmStickSpecs().getSample());
		dbUtil.writeStimObjData(getStimObjIds().getSample(), sampleSpec.toXml(), sampleMStickObjData.toXml());
	}

	private void writeMatchSpec() {
		NoisyPngSpecWriter matchSpecWriter = NoisyPngSpecWriter.createWithoutNoiseMap(
				getCoords().getMatch(),
				getPngPaths().getMatch(),
				trialParameters.getSize());
		matchSpecWriter.writeSpec();
		NoisyPngSpec matchSpec = matchSpecWriter.getSpec();
	
		MStickStimObjData matchMStickObjData = new MStickStimObjData("Match", getmStickSpecs().getMatch());
		dbUtil.writeStimObjData(getStimObjIds().getMatch(), matchSpec.toXml(), matchMStickObjData.toXml());
	}
	
	protected abstract void writeDistractorSpecs();

	protected abstract NAFC<String> getPngPaths();

	protected abstract NAFC<AllenMStickSpec> getmStickSpecs();

	protected abstract NAFC<Coordinates2D> getCoords();

	protected abstract NAFC<Long> getStimObjIds();

}
