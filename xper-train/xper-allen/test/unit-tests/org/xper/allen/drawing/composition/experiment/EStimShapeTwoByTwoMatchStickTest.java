package org.xper.allen.drawing.composition.experiment;

import org.junit.Before;
import org.junit.Test;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper;
import org.xper.allen.drawing.ga.TestMatchStickDrawer;
import org.xper.allen.pga.RFStrategy;

import static org.xper.allen.drawing.composition.experiment.TwoByTwoMatchStickTest.PARTIAL_RF;

public class EStimShapeTwoByTwoMatchStickTest {

    private TwoByTwoMatchStick baseMStick;
    private TestMatchStickDrawer testMatchStickDrawer;
    private String figPath;

    @Before
    public void setUp() throws Exception {
        testMatchStickDrawer = new TestMatchStickDrawer();
        testMatchStickDrawer.setup(500, 500);

        baseMStick = new TwoByTwoMatchStick(new GaussianNoiseMapper());
        baseMStick.setMaxAttempts(-1);
        baseMStick.setProperties(8, "SHADE");
        baseMStick.genMatchStickRand();

        figPath = "/home/r2_allen/Pictures";


    }

    @Test
    public void test_partially_inside(){
        EStimShapeTwoByTwoMatchStick firstMStick = new EStimShapeTwoByTwoMatchStick(RFStrategy.PARTIALLY_INSIDE, PARTIAL_RF, null);
        firstMStick.setProperties(5, "SHADE");
        firstMStick.genMatchStickFromComponent(baseMStick, 1, 2, firstMStick.maxAttempts);
        testMatchStickDrawer.drawMStick(firstMStick);
        testMatchStickDrawer.drawCompMap(firstMStick);
        testMatchStickDrawer.saveImage(figPath + "/firstMStick");
        testMatchStickDrawer.clear();


        EStimShapeTwoByTwoMatchStick secondMStick = new EStimShapeTwoByTwoMatchStick(RFStrategy.PARTIALLY_INSIDE, PARTIAL_RF, null);
        secondMStick.setProperties(5, "SHADE");
        secondMStick.genMorphedBaseMatchStick(firstMStick, 1, secondMStick.maxAttempts, true, true, 0.7, 1 / 3.0);
        testMatchStickDrawer.drawMStick(secondMStick);
        testMatchStickDrawer.drawCompMap(secondMStick);
        testMatchStickDrawer.saveImage(figPath + "/secondMStick");
        testMatchStickDrawer.clear();

        EStimShapeTwoByTwoMatchStick thirdMStick = new EStimShapeTwoByTwoMatchStick(RFStrategy.PARTIALLY_INSIDE, PARTIAL_RF, null);
        thirdMStick.setProperties(5, "SHADE");
        thirdMStick.genMorphedDrivingComponentMatchStick(firstMStick, 0.5, 0.5, true, true, firstMStick.maxAttempts);
        testMatchStickDrawer.drawMStick(thirdMStick);
        testMatchStickDrawer.drawCompMap(thirdMStick);
        testMatchStickDrawer.saveImage(figPath + "/thirdMStick");
        testMatchStickDrawer.clear();

        EStimShapeTwoByTwoMatchStick fourthMStick = new EStimShapeTwoByTwoMatchStick(RFStrategy.PARTIALLY_INSIDE, PARTIAL_RF, null);
        fourthMStick.setProperties(5, "SHADE");
        fourthMStick.genSwappedBaseAndDrivingComponentMatchStick(secondMStick, 1, thirdMStick, true, 15);
        testMatchStickDrawer.drawMStick(fourthMStick);
        testMatchStickDrawer.drawCompMap(fourthMStick);
        testMatchStickDrawer.saveImage(figPath + "/fourthMStick");
        testMatchStickDrawer.clear();


    }
}