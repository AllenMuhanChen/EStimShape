package org.xper.allen.nafc.blockgen;


import static org.xper.allen.nafc.blockgen.NAFCBlockGen.randomWithinRadius;

import java.util.ArrayList;
import java.util.LinkedList;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.IntStream;

import org.xper.drawing.Coordinates2D;

public abstract class NAFCBlockGen {
	
	protected static int[] frequencyToNumTrials(double[] typesFrequencies, int numTrials) {
		int[] typesNumTrials = new int[typesFrequencies.length];
		for(int i=0; i<typesFrequencies.length; i++) {
			typesNumTrials[i] = (int) Math.round((double) numTrials * typesFrequencies[i]);
		}
		if(IntStream.of(typesNumTrials).sum()!= numTrials) {
			throw new IllegalArgumentException("Total Round(numTrials .* Frequencies) should = numTrials");
		}
		return typesNumTrials;
	}
	
	/**
	 * generic method for returning a list of trials<K> 
	 * @param <K>
	 * @param numTrials: totla number of trials in block being generated. Used to double check input is correct
	 * @param types: array of types <K>
	 * @param typesNumTrials: number of trials for each type
	 * @return
	 */
	protected <K> List<K> populateTrials(int numTrials, K[] types, int[] typesNumTrials) {
		if(IntStream.of(typesNumTrials).sum()!= numTrials) {
			throw new IllegalArgumentException("Total typesNumTrials should equal total numTrials");
		}
		List<K> trialList = new LinkedList<>();
		int numTypes = types.length;
		for(int i=0; i<numTypes; i++) {
			for (int j=0; j<typesNumTrials[i]; j++) {
				trialList.add(types[i]);
			}
		}
		return trialList;
	}

	
	/**
	 * populating using frequency. 
	 * @param <K>
	 * @param numTrials
	 * @param types
	 * @param typesFrequency
	 * @return
	 */
	protected <K> List<K> populateTrials(int numTrials, K[] types, double[] typesFrequency) {
		int[] typesNumTrials = new int[types.length];
		for(int i=0; i<types.length; i++) {
			typesNumTrials[i] = (int) Math.round(typesFrequency[i]* (double) numTrials);
		}
		if(IntStream.of(typesNumTrials).sum()!= numTrials) {
			throw new IllegalArgumentException("Total number of trials rounded from frequencies does not equal correct total num of trials");
		}
		
		List<K> trialList = new LinkedList<>();
		int numTypes = types.length;
		for(int i=0; i<numTypes; i++) {
			for (int j=0; j<typesNumTrials[i]; j++) {
				trialList.add(types[i]);
			}
		}
		return trialList;
	}
	
	protected static Coordinates2D randomChoice(double lowerRadiusLim, double upperRadiusLim){
		return randomWithinRadius(lowerRadiusLim, upperRadiusLim);

	}
	
	/**
	 * Class to aid in creating equally radially spaced choices, but allow the distractors to be further from center. 
	 * @author r2_allen
	 *
	 */
	public class DistancedDistractorsUtil {
		int numChoices;
		double lowerRadiusLim;
		double upperRadiusLim;
		double distractorDistanceLowerLim;
		double distractorDistanceUpperLim;

		Double[] distractor_angles;
		Double[] distractor_radii;
		ArrayList<Coordinates2D> distractor_coords;

		double match_angle;
		double match_radii;
		Coordinates2D match_coords;

		public DistancedDistractorsUtil(int numChoices, double lowerRadiusLim, double upperRadiusLim, double distractorDistanceLowerLim, double distractorDistanceUpperLim){
			this.numChoices = numChoices;
			this.lowerRadiusLim = lowerRadiusLim;
			this.upperRadiusLim = upperRadiusLim;
			this.distractorDistanceLowerLim = distractorDistanceLowerLim;
			this.distractorDistanceUpperLim = distractorDistanceUpperLim;

			distractor_angles = new Double[numChoices-1];
			distractor_radii = new Double[numChoices-1];
			distractor_coords = new ArrayList<Coordinates2D>();

			double distractorDistance = inclusiveRandomDouble(distractorDistanceLowerLim, distractorDistanceUpperLim);

			match_angle = ThreadLocalRandom.current().nextDouble() * 2 * Math.PI;
			double baseRadii = Math.sqrt(ThreadLocalRandom.current().nextDouble()) * (upperRadiusLim-lowerRadiusLim) + lowerRadiusLim;
			match_radii = baseRadii;
			match_coords = polarToCart(match_radii, match_angle);

			double step = 2 * Math.PI / numChoices;
			for (int i=0; i < numChoices-1; i++){
				if(i==0){
					distractor_angles[i] = match_angle + step; //step the angle
				}
				else{
					distractor_angles[i] = distractor_angles[i-1] + step;
				}
				distractor_radii[i] = baseRadii + distractorDistance; //keep radius the same
				distractor_coords.add(polarToCart(distractor_radii[i], distractor_angles[i])); //polar to cartesian
			}
		}

		public Coordinates2D getMatchCoords(){
			return match_coords;
		}

		/**
		 * get the coords of one of the distractors, then remove it 
		 * @return
		 */
		public Coordinates2D getDistractorCoords(){
			Coordinates2D output = distractor_coords.get(0);
			distractor_coords.remove(0);

			return output;
		}

		/**
		 * 
		 * @return
		 */
		public List<Coordinates2D> getDistractorCoordsAsList(){

			return distractor_coords;
		}



	}

	
	/**
	 * Specifies locations choices such that they are equidistant (Angular) from each other and organized in a ring around the center. 
	 * For example, if there are two choices, they will be 180 degrees apart. If three choices, they will be 120 degrees apart. 
	 * @param lowerRadiusLim
	 * @param upperRadiusLim
	 * @param numChoices
	 * @return
	 */
	protected static Coordinates2D[] equidistantRandomChoices(double lowerRadiusLim, double upperRadiusLim, int numChoices){
		Coordinates2D[] output = new Coordinates2D[numChoices];
		Double[] angles = new Double[numChoices];
		Double[] radii = new Double[numChoices];

		angles[0] = ThreadLocalRandom.current().nextDouble() * 2 * Math.PI;
		radii[0] = Math.sqrt(ThreadLocalRandom.current().nextDouble()) * (upperRadiusLim-lowerRadiusLim) + lowerRadiusLim;
		output[0] = polarToCart(radii[0], angles[0]);

		if (numChoices==1){
			return output;
		}
		else{
			double step = 2 * Math.PI / numChoices;
			for (int i=1; i < numChoices; i++){
				angles[i] = angles[i-1] + step; //step the angle
				radii[i] = radii[i-1]; //keep radius the same
				output[i] = polarToCart(radii[i], angles[i]); //polar to cartesian
			}
			return output;
		}
	}
	

	protected static double inclusiveRandomDouble(double val1, double val2) {
		if (val2>val1){
			return ThreadLocalRandom.current().nextDouble(val1, val2);
		}
		else {
			return val1;
		}

	}

	protected static Coordinates2D randomWithinRadius(double lowerLim, double upperLim) {

		double r = Math.sqrt(ThreadLocalRandom.current().nextDouble()) * (upperLim-lowerLim) + lowerLim;
		double theta = ThreadLocalRandom.current().nextDouble() * 2 * Math.PI;

		Coordinates2D output = polarToCart(r, theta);
		return output;
	}

	protected static Coordinates2D polarToCart(double r, double theta){
		Coordinates2D output = new Coordinates2D(); 
		double x = 0 + r * Math.cos(theta);
		double y = 0 + r * Math.sin(theta);
		output.setX(x);
		output.setY(y);
		return output;
	}
}
