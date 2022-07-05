package org.xper.allen.nafc.blockgen;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;

import org.xper.allen.drawing.composition.AllenMatchStick;

public class RandDistractorGenerator {

	NumberOfDistractors numDistractors;
	AbstractPsychometricNoiseMapGenerator gen;
	private List<Long> randDistractorsIds = new LinkedList<Long>();
	
	public RandDistractorGenerator(NumberOfDistractors numDistractors, AbstractPsychometricNoiseMapGenerator gen,
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
		System.out.println("Trying to Generate Rand Distractor");
		objs_randDistractor = new ArrayList<>();
		boolean tryagain = true;
		while(tryagain) {
			objs_randDistractor = new ArrayList<>();
			for(int i=0; i<numDistractors.numPsychometricDistractors; i++) {
				objs_randDistractor.add(new AllenMatchStick());
			}
			boolean randDistractorsSuccess = false;
			Boolean[] randDistractorSuccess = new Boolean[numDistractors.numPsychometricDistractors];
			for(int b=0; b<randDistractorSuccess.length; b++) randDistractorSuccess[b]=false;
			for(int j=0; j<numDistractors.numPsychometricDistractors; j++) {
				try {
					gen.setProperties(objs_randDistractor.get(j));
					objs_randDistractor.get(j).genMatchStickRand();
					randDistractorSuccess[j] = true;
				} catch(Exception e) {
					e.printStackTrace();
					randDistractorSuccess[j] = false;
				}
				if(!randDistractorSuccess[j]) {
					objs_randDistractor.set(j, new AllenMatchStick());
				}
			}
			randDistractorsSuccess = !Arrays.asList(randDistractorSuccess).contains(false);

			if(randDistractorsSuccess) {
				tryagain = false;
			}
		}
	}

	List<String> randDistractorsPngPaths = new LinkedList<String>();
	
	private void drawRandDistractors() {
		List<String> sampleLabels = Arrays.asList(new String[] {"sample"});
		int indx=0;
		for (AllenMatchStick obj: objs_randDistractor) {
			String path = gen.pngMaker.createAndSavePNGFromObj(obj, randDistractorsIds.get(indx), sampleLabels);
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
