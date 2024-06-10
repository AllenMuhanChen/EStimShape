package org.xper.allen.drawing.composition.experiment;

import org.junit.Before;
import org.junit.Test;
import org.xper.allen.drawing.ga.TestMatchStickDrawer;
import org.xper.allen.pga.RFStrategy;

import static org.junit.Assert.*;
import static org.xper.allen.drawing.composition.experiment.TwobyTwoMatchStickTest.PARTIAL_RF;

public class EStimShapeTwoByTwoMatchStickTest {

    private TwobyTwoMatchStick baseMStick;
    private TestMatchStickDrawer testMatchStickDrawer;
    private String figPath;

    @Before
    public void setUp() throws Exception {
        testMatchStickDrawer = new TestMatchStickDrawer();
        testMatchStickDrawer.setup(500, 500);

        baseMStick = new TwobyTwoMatchStick();
        baseMStick.setMaxAttempts(-1);
        baseMStick.setProperties(8, "SHADE");
        baseMStick.genMatchStickRand();

        figPath = "/home/r2_allen/Pictures";


    }

    @Test
    public void test_partially_inside(){
        EStimShapeTwoByTwoMatchStick firstMStick = new EStimShapeTwoByTwoMatchStick(RFStrategy.PARTIALLY_INSIDE, PARTIAL_RF);
        firstMStick.setProperties(5, "SHADE");
        firstMStick.genMatchStickFromComponent(baseMStick, 1, 2);
        testMatchStickDrawer.drawMStick(firstMStick);
        testMatchStickDrawer.drawCompMap(firstMStick);
        testMatchStickDrawer.saveImage(figPath + "/firstMStick");
        testMatchStickDrawer.clear();


        EStimShapeTwoByTwoMatchStick secondMStick = new EStimShapeTwoByTwoMatchStick(RFStrategy.PARTIALLY_INSIDE, PARTIAL_RF);
        secondMStick.setProperties(5, "SHADE");
        secondMStick.genNewBaseMatchStick(firstMStick, 1);
        testMatchStickDrawer.drawMStick(secondMStick);
        testMatchStickDrawer.drawCompMap(secondMStick);
        testMatchStickDrawer.saveImage(figPath + "/secondMStick");
        testMatchStickDrawer.clear();

        EStimShapeTwoByTwoMatchStick thirdMStick = new EStimShapeTwoByTwoMatchStick(RFStrategy.PARTIALLY_INSIDE, PARTIAL_RF);
        thirdMStick.setProperties(5, "SHADE");
        thirdMStick.genNewDrivingComponentMatchStick(firstMStick, 0.5, 0.5);
        testMatchStickDrawer.drawMStick(thirdMStick);
        testMatchStickDrawer.drawCompMap(thirdMStick);
        testMatchStickDrawer.saveImage(figPath + "/thirdMStick");
        testMatchStickDrawer.clear();

        EStimShapeTwoByTwoMatchStick fourthMStick = new EStimShapeTwoByTwoMatchStick(RFStrategy.PARTIALLY_INSIDE, PARTIAL_RF);
        fourthMStick.setProperties(5, "SHADE");
        fourthMStick.genFourthMatchStick(secondMStick, 1, thirdMStick);
        testMatchStickDrawer.drawMStick(fourthMStick);
        testMatchStickDrawer.drawCompMap(fourthMStick);
        testMatchStickDrawer.saveImage(figPath + "/fourthMStick");
        testMatchStickDrawer.clear();


    }
}