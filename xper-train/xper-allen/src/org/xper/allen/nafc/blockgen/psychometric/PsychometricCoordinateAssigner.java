package org.xper.allen.nafc.blockgen.psychometric;

import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.DistancedDistractorsUtil;
import org.xper.allen.nafc.blockgen.NAFCCoordinateAssigner;
import org.xper.allen.nafc.blockgen.NAFCCoordinates;
import org.xper.drawing.Coordinates2D;

public class PsychometricCoordinateAssigner extends NAFCCoordinateAssigner{
	
	
	Lims sampleDistanceLims;
	int numChoices;
	
	public PsychometricCoordinateAssigner(Lims sampleDistanceLims, int numChoices) {
		super();
		this.sampleDistanceLims = sampleDistanceLims;
		this.numChoices = numChoices;
	}

	private DistancedDistractorsUtil ddUtil;
	
	NAFCCoordinates coords = new NAFCCoordinates();
	public void assignCoords() {
		assignSampleCoords();
		setUpDDUtil();
		assignMatchCoords();
		assignDistractorCoords();
	}



	private void assignSampleCoords() {
		Coordinates2D sampleCoords = randomCoordsWithinRadii(sampleDistanceLims.getLowerLim(), sampleDistanceLims.getUpperLim());
		coords.setSampleCoords(sampleCoords);
	}

	private void setUpDDUtil() {
		int distractorDistanceLowerLim = 0;
		int distractorDistanceUpperLim = 0;
		ddUtil = new DistancedDistractorsUtil(
				numChoices,
				sampleDistanceLims.getLowerLim(),
				sampleDistanceLims.getUpperLim(),
				distractorDistanceLowerLim,
				distractorDistanceUpperLim);
	}
	
	private void assignMatchCoords() {
		coords.setMatchCoords(ddUtil.getMatchCoords());
	}
	
	private void assignDistractorCoords() {
		coords.setDistractorCoords(ddUtil.getDistractorCoordsAsList());
	}
	
	public NAFCCoordinates getCoords() {
		return coords;
	}
}
