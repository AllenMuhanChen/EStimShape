package org.xper.allen.nafc.blockgen.psychometric;

import org.xper.allen.nafc.blockgen.Lims;

import java.util.List;

import org.xper.allen.nafc.blockgen.NAFCCoordinateAssigner;
import org.xper.allen.nafc.blockgen.NumberOfDistractorsForPsychometricTrial;
import org.xper.drawing.Coordinates2D;

public class PsychometricCoordinateAssigner extends NAFCCoordinateAssigner{

	NumberOfDistractorsForPsychometricTrial numDistractors;
	private Psychometric<Coordinates2D> coords = new Psychometric<>();

	public PsychometricCoordinateAssigner(Lims sampleDistanceLims, NumberOfDistractorsForPsychometricTrial numDistractors, Lims choiceDistanceLims) {
		super(numDistractors.numTotal+1, sampleDistanceLims, choiceDistanceLims);
		this.numDistractors = numDistractors;
		assignCoords();
	}

	@Override
	protected void assignDistractorCoords() {
		List<Coordinates2D> allDistractors = ddUtil.getDistractorCoordsAsList();
		for(int i = 0; i< numDistractors.getNumPsychometricDistractors(); i++) {
			getCoords().addPsychometricDistractor(allDistractors.get(i));
		}
		for(int i = 0; i< numDistractors.getNumRandDistractors(); i++) {
			getCoords().addRandDistractor(allDistractors.get(numDistractors.getNumPsychometricDistractors() +i));
		}
	}

	@Override
	public Psychometric<Coordinates2D> getCoords() {
		return coords;
	}

}
