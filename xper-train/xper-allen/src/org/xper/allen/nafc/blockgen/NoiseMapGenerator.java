package org.xper.allen.nafc.blockgen;

import java.util.LinkedList;
import java.util.List;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.nafc.vo.NoiseData;
import org.xper.allen.nafc.vo.NoiseType;

public class NoiseMapGenerator {

	
	private String noiseMapPath;
	
	long id;
	AbstractPsychometricNoiseMapGenerator gen;
	AllenMatchStick obj;
	AllenMStickSpec mStickSpec;
	PsychometricIds psychometricIds;
	public NoiseMapGenerator(AllenMatchStick mStick, PsychometricIds psychometricIds, AbstractPsychometricNoiseMapGenerator gen, double[] noiseChance,
			 long id) {
		super();
		this.obj = mStick;
		this.id = id;
		this.gen = gen;
		this.noiseChance = noiseChance;
		this.psychometricIds = psychometricIds;
	}

	
	public void generate() {
//		fetchObj();
		assignParamsForNoiseMapGen();
		prepareNoiseMap();
	}
	

//	private void fetchObj() {
//		AllenMatchStick ams = new AllenMatchStick();
//		gen.setProperties(ams);
//		ams.genMatchStickFromFile(specPath);
//		obj = ams;
//	}
	
	NoiseData noiseData;
	double[] noiseChance;
	/**
	 * Assign parameters required to generate a noise map from the sample
	 * @param psychometricIds.getSetId()
	 * @param psychometricIds.getStimId()
	 */
	private void assignParamsForNoiseMapGen() {
		noiseData = new NoiseData(NoiseType.PRE_JUNC, NoisyMStickPngPsychometricBlockGen.noiseNormalizedPosition_PRE_JUNC, noiseChance);
		obj.setNoiseParameters(noiseData);
	}
	
	private void prepareNoiseMap() {
		String generatorNoiseMapPath = generateNoiseMap();
		noiseMapPath = gen.convertNoiseMapPathToExperiment(generatorNoiseMapPath);
	}
	
	
	private String generateNoiseMap() {
		List<String> noiseMapLabels = new LinkedList<String>();
		noiseMapLabels.add(Long.toString(psychometricIds.setId));
		noiseMapLabels.add(Integer.toString(psychometricIds.stimId));
		return gen.pngMaker.createAndSaveNoiseMapFromObj(obj, id, noiseMapLabels);
	}


	public String getNoiseMapPath() {
		return noiseMapPath;
	}

}
