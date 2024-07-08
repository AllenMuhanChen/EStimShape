package org.xper.allen.nafc.blockgen.psychometric;

import java.util.LinkedList;
import java.util.List;

import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.NoiseMapGenerator;
import org.xper.allen.nafc.vo.NoiseParameters;

public class PsychometricNoiseMapGenerator extends NoiseMapGenerator {

	AbstractPsychometricTrialGenerator generator;
	PsychometricIds psychometricIds;
	NoiseParameters noiseParameters;

	public PsychometricNoiseMapGenerator(AllenMatchStick mStick, Long id, PsychometricIds psychometricIds, AbstractPsychometricTrialGenerator gen,
										 NoiseParameters noiseParameters) {
		super();
		this.generator = gen;
		this.id = id;
		this.mStick = mStick;
		this.psychometricIds = psychometricIds;
		this.noiseParameters = noiseParameters;

		generate();
	}


	@Override
	protected void assignParamsForNoiseMapGen() {
		mStick.setNoiseParameters(noiseParameters);
	}


	@Override
	protected void generateNoiseMap() {
		AllenPNGMaker pngMaker = generator.getPngMaker();
		pngMaker.createDrawerWindow();
		List<String> noiseMapLabels = new LinkedList<String>();
		noiseMapLabels.add(Long.toString(psychometricIds.setId));
		noiseMapLabels.add(Integer.toString(psychometricIds.stimId));
		String generatorNoiseMapPath = pngMaker.createAndSaveCompGraphNoiseMap(mStick, id, noiseMapLabels, generator.getGeneratorPsychometricNoiseMapPath());

		experimentNoiseMapPath = generator.convertPsychometricToExperiment(generatorNoiseMapPath);
	}




}