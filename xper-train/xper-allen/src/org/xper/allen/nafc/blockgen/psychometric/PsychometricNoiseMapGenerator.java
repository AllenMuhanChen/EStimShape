package org.xper.allen.nafc.blockgen.psychometric;

import java.util.LinkedList;
import java.util.List;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.NoiseMapGenerator;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.nafc.vo.NoiseParameters;
import org.xper.allen.nafc.vo.NoiseType;

public class PsychometricNoiseMapGenerator extends NoiseMapGenerator {

	AbstractPsychometricTrialGenerator generator;
	PsychometricIds psychometricIds;
	NoiseParameters noiseParameters;

	public PsychometricNoiseMapGenerator(AllenMatchStick mStick, PsychometricIds psychometricIds, AbstractPsychometricTrialGenerator gen, double[] noiseChance,
			 long id, NoiseParameters noiseParameters) {
		super();
		this.generator = gen;
		this.id = id;
		this.mStick = mStick;
		this.noiseChance = noiseChance;
		this.psychometricIds = psychometricIds;
		this.noiseParameters = noiseParameters;
		
		generate();
	}


	
	double[] noiseChance;
	
	@Override
	protected void assignParamsForNoiseMapGen() {
		mStick.setNoiseParameters(noiseParameters);
	}
	
	
	@Override
	protected void generateNoiseMap() {
		
		List<String> noiseMapLabels = new LinkedList<String>();
		noiseMapLabels.add(Long.toString(psychometricIds.setId));
		noiseMapLabels.add(Integer.toString(psychometricIds.stimId));
		String generatorNoiseMapPath = generator.getPngMaker().createAndSaveNoiseMap(mStick, id, noiseMapLabels, generator.getGeneratorPsychometricNoiseMapPath());
		
		noiseMapPath = generator.convertPsychometricToExperiment(generatorNoiseMapPath);
		
	}




}