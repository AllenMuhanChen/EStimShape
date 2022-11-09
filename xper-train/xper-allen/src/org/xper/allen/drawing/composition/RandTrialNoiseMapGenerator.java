package org.xper.allen.drawing.composition;

import java.util.LinkedList;
import java.util.List;

import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.nafc.vo.NoiseParameters;

public class RandTrialNoiseMapGenerator extends NoiseMapGenerator {
	
	private NoiseParameters noiseParameters;
	AbstractMStickPngTrialGenerator generator;
	

	public RandTrialNoiseMapGenerator(long id, AllenMatchStick mStick, NoiseParameters noiseParameters,
			AbstractMStickPngTrialGenerator generator) {
		super(id, mStick);
		this.noiseParameters = noiseParameters;
		this.generator = generator;
		
		generate();
	}

	@Override
	protected void assignParamsForNoiseMapGen() {
		mStick.setNoiseParameters(noiseParameters);
	}


	@Override
	protected void generateNoiseMap() {
		List<String> noiseMapLabels = new LinkedList<>();
		noiseMapLabels.add("sample");
		generator.getPngMaker().createDrawerWindow();
		String generatorNoiseMapPath = generator.getPngMaker().createAndSaveNoiseMap(mStick, id, noiseMapLabels, generator.getGeneratorPngPath());
		experimentNoiseMapPath = generator.convertPathToExperiment(generatorNoiseMapPath);
	}
}
