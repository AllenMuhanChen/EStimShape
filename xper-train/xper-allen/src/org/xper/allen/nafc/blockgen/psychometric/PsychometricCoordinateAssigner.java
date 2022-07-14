package org.xper.allen.nafc.blockgen.psychometric;

import org.xper.allen.nafc.blockgen.Lims;

import java.util.List;

import org.xper.allen.nafc.blockgen.NAFCCoordinateAssigner;
import org.xper.allen.nafc.blockgen.NAFCCoordinates;
import org.xper.allen.nafc.blockgen.NumberOfDistractors;
import org.xper.drawing.Coordinates2D;

public class PsychometricCoordinateAssigner extends NAFCCoordinateAssigner{

	NumberOfDistractors numDistractors; 
	
	public PsychometricCoordinateAssigner(Lims sampleDistanceLims, NumberOfDistractors numDistractors) {
		super(numDistractors.numTotal+1, sampleDistanceLims);
		this.numDistractors = numDistractors;
		
		assignCoords();
	}

	@Override
	protected void assignDistractorCoords() {
		List<Coordinates2D> allDistractors = ddUtil.getDistractorCoordsAsList();
		for(int i=0; i<numDistractors.numPsychometricDistractors; i++) {
			coords.addPsychometricDistractor(allDistractors.get(i));
		}
		for(int i=0; i<numDistractors.numRandDistractors; i++) {
			coords.addRandDistractor(allDistractors.get(numDistractors.numPsychometricDistractors+i));
		}
	}
}
