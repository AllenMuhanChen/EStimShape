package org.xper.allen.nafc.blockgen;

import java.util.concurrent.ThreadLocalRandom;

import org.xper.drawing.Coordinates2D;

public abstract class ChoiceCoordinateAssigner{
	
	protected static double inclusiveRandomDouble(double val1, double val2) {
		if (val2>val1){
			return ThreadLocalRandom.current().nextDouble(val1, val2);
		}
		else {
			return val1;
		}
	}

	protected static Coordinates2D randomCoordsWithinRadii(double lowerLim, double upperLim) {

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
	
	protected static Coordinates2D randomChoice(double lowerRadiusLim, double upperRadiusLim){
		return randomCoordsWithinRadii(lowerRadiusLim, upperRadiusLim);
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
	
	
}
