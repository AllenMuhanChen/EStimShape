package org.xper.allen.nafc.blockgen.rand;

import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.NAFCCoordinateAssigner;
import org.xper.drawing.Coordinates2D;

import java.util.List;


public class RandTrialCoordinateAssigner extends NAFCCoordinateAssigner {

    private NumberOfDistractorsForRandTrial numDistractors;
    private Rand<Coordinates2D> coords = new Rand<>();

    public RandTrialCoordinateAssigner(Lims sampleDistanceLims, NumberOfDistractorsForRandTrial numDistractors) {
        super(numDistractors.getTotalNumDistractors()+1, sampleDistanceLims);
        this.numDistractors = numDistractors;
        assignCoords();
    }

    @Override
    protected void assignDistractorCoords(){
        List<Coordinates2D> allDistractors = ddUtil.getDistractorCoordsAsList();
        for(int i=0; i<numDistractors.getNumQMDistractors(); i++) {
            getCoords().addQualitativeMorphDistractor(allDistractors.get(i));
        }
        for(int i=0; i<numDistractors.getNumRandDistractors(); i++) {
            getCoords().addRandDistractor(allDistractors.get(numDistractors.getNumQMDistractors()+i));
        }
    }

    @Override
    public Rand<Coordinates2D> getCoords() {
        return coords;
    }
}
