package org.xper.allen.nafc.blockgen;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;

import org.xper.allen.drawing.composition.AbstractMStickGenerator;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.FromRandLeafMStickGenerator;
import org.xper.allen.nafc.blockgen.psychometric.AbstractPsychometricTrialGenerator;

public class PNGDrawer {

	NumberOfDistractorsForPsychometricTrial numDistractors;
	AbstractMStickPngTrialGenerator gen;
	private List<Long> randDistractorsIds = new LinkedList<Long>();
	
	public PNGDrawer(NumberOfDistractorsForPsychometricTrial numDistractors, AbstractPsychometricTrialGenerator gen,
                     List<Long> randDistractorsIds, List<String> randDistractorsPngPaths) {
		super();
		this.numDistractors = numDistractors;
		this.gen = gen;
		this.randDistractorsIds = randDistractorsIds;
		this.randDistractorsPngPaths = randDistractorsPngPaths;
	}

	List<AllenMatchStick> objs_randDistractor = new ArrayList<AllenMatchStick>();
	
	public void genRandDistractors() {
		genRandDistractors_obj();
		drawRandDistractors();
		
	}
	
	private void genRandDistractors_obj() {

		boolean tryagain = true;
		while(tryagain) {
			objs_randDistractor = new ArrayList<AllenMatchStick>();
			
			for(int j = 0; j< numDistractors.getNumRandDistractors(); j++) {
				try {
					AbstractMStickGenerator objGenerator = new FromRandLeafMStickGenerator(gen.getMaxImageDimensionDegrees());
					objGenerator.getMStick();
					objs_randDistractor.add(objGenerator.getMStick());
					if(objGenerator.isSuccessful()) {
						tryagain = false;
					}
				} catch(Exception e) {
					e.printStackTrace();
					objs_randDistractor.set(j, new AllenMatchStick());
					tryagain = true;
				}
			}
		}
	}

	List<String> randDistractorsPngPaths = new LinkedList<String>();
	private void drawRandDistractors() {
		List<String> sampleLabels = Arrays.asList(new String[] {"sample"});
		int indx=0;
		for (AllenMatchStick obj: objs_randDistractor) {
			String path = gen.pngMaker.createAndSavePNG(obj, randDistractorsIds.get(indx), sampleLabels, gen.getGeneratorPngPath());
			gen.convertPathToExperiment(path);
			randDistractorsPngPaths.add(path);
		}
	}

	public List<String> getRandDistractorsPngPaths() {
		return randDistractorsPngPaths;
	}

	public List<AllenMatchStick> getObjs_randDistractor() {
		return objs_randDistractor;
	}

	public void setObjs_randDistractor(List<AllenMatchStick> objs_randDistractor) {
		this.objs_randDistractor = objs_randDistractor;
	}
}
