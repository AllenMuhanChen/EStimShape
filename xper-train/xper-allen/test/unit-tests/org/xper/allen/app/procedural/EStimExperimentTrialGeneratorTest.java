package org.xper.allen.app.procedural;

import org.junit.Test;
import org.xper.allen.app.estimshape.EStimExperimentTrialGenerator;
import org.xper.allen.drawing.ga.CircleReceptiveField;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.drawing.Coordinates2D;

import java.util.List;
import java.util.function.Predicate;

import static org.junit.Assert.assertEquals;

public class EStimExperimentTrialGeneratorTest {

    @Test
    public void testAssigningRFs() {
        int numEStimTrials = 10;
        int numDeltaTrials = 10;
        int numBehavioralTrials = 60;
        CircleReceptiveField realRF = new CircleReceptiveField(new Coordinates2D(0, 10), 10);
        List<ReceptiveField> behTrialRFs = EStimExperimentTrialGenerator.assignRFsToBehTrials(numEStimTrials, numDeltaTrials, numBehavioralTrials, realRF);

        assertEquals(60, behTrialRFs.size());
        //real RF is assigned number of beh trials equal to number of test trials
        Predicate<ReceptiveField> isRealRF = rf -> rf == realRF;
        long numRealRF = behTrialRFs.stream().filter(isRealRF).count();
        assertEquals(20, numRealRF);

        //fake RFs are assigned number of beh trials equal to numBehavioralTrials - numTestTrials
        Predicate<ReceptiveField> isFakeRF = rf -> rf != realRF;
        long numFakeRF = behTrialRFs.stream().filter(isFakeRF).count();
        assertEquals(40, numFakeRF);


    }
}