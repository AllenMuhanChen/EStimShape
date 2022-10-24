package org.xper.allen.nafc.blockgen.rand;

import org.junit.Test;
import org.xper.allen.drawing.composition.noisy.NoisePositions;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.vo.NoiseParameters;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.drawing.Coordinates2D;

import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

import static junit.framework.Assert.assertTrue;

public class RandTrialCoordinateAssignerTest {

    private Lims sampleDistanceLims;
    private Lims choiceDistanceLims;
    private int size;
    private int eyeWinSize;
    private NoiseType noiseType;
    private Lims noiseChance;
    private NoiseParameters noiseParameters;
    private RandNoisyTrialParameters trialParameters;
    private NumberOfDistractorsForRandTrial numDistractors;
    private NumberOfMorphCategories numMorphCategories;

    @Test
    public void coords_are_radially_spaced() {
        int numQMDistractors = 1;
        int numRandDistractors = 1;
        numDistractors = new NumberOfDistractorsForRandTrial(numQMDistractors, numRandDistractors);
        sampleDistanceLims = new Lims(0, 5);
        choiceDistanceLims = new Lims(9, 10);
        size = 10;
        eyeWinSize = 10;
        noiseType = NoiseType.NONE;
        noiseChance = new Lims(0.5,0.5);
        noiseParameters = new NoiseParameters(noiseType, new NoisePositions(0.0,0.0), noiseChance);
        int numMMCategories = 1;
        int numQMCategories = 1;
        numMorphCategories = new NumberOfMorphCategories(numMMCategories, numQMCategories);
        trialParameters = new RandNoisyTrialParameters(
                sampleDistanceLims,
                choiceDistanceLims,
                size,
                eyeWinSize,
                noiseParameters,
                numDistractors,
                numMorphCategories);

        RandTrialCoordinateAssigner coordAssigner = new RandTrialCoordinateAssigner(trialParameters.getSampleDistanceLims(), trialParameters.getNumDistractors(), trialParameters.getChoiceDistanceLims());

        Rand<Coordinates2D> coords = coordAssigner.getCoords();

        coords_have_same_distance_from_origin(coords);

    }


    private void coords_have_same_distance_from_origin(Rand<Coordinates2D> coords) {
        Coordinates2D origin = new Coordinates2D(0, 0);
        List<Coordinates2D> choices = new LinkedList<Coordinates2D>();
        choices.add(coords.getMatch());
        choices.addAll(coords.getAllDistractors());

        List<Long> radii = new LinkedList<Long>();
        for (Coordinates2D choice : choices) {
            radii.add(Math.round(choice.distance(origin) * 100) / 100);
        }

        assertTrue(Collections.frequency(radii, radii.get(0)) == radii.size());
    }

}
