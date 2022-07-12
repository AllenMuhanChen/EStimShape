package org.xper.allen.nafc.blockgen;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

import org.xper.drawing.Coordinates2D;

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

		double distractorDistance = ChoiceCoordinateAssigner.inclusiveRandomDouble(distractorDistanceLowerLim, distractorDistanceUpperLim);

		match_angle = ThreadLocalRandom.current().nextDouble() * 2 * Math.PI;
		double baseRadii = Math.sqrt(ThreadLocalRandom.current().nextDouble()) * (upperRadiusLim-lowerRadiusLim) + lowerRadiusLim;
		match_radii = baseRadii;
		match_coords = ChoiceCoordinateAssigner.polarToCart(match_radii, match_angle);

		double step = 2 * Math.PI / numChoices;
		for (int i=0; i < numChoices-1; i++){
			if(i==0){
				distractor_angles[i] = match_angle + step; //step the angle
			}
			else{
				distractor_angles[i] = distractor_angles[i-1] + step;
			}
			distractor_radii[i] = baseRadii + distractorDistance; //keep radius the same
			distractor_coords.add(ChoiceCoordinateAssigner.polarToCart(distractor_radii[i], distractor_angles[i])); //polar to cartesian
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