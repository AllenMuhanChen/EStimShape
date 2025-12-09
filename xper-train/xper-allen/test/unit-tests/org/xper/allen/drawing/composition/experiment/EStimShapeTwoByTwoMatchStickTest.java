package org.xper.allen.drawing.composition.experiment;

import org.junit.Before;
import org.junit.Test;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper;
import org.xper.allen.drawing.ga.TestMatchStickDrawer;
import org.xper.allen.pga.RFStrategy;

import java.util.Collections;

import static org.xper.allen.drawing.composition.experiment.TwoByTwoMatchStickTest.PARTIAL_RF;

public class EStimShapeTwoByTwoMatchStickTest {

    private TwoByTwoMatchStick baseMStick;
    private TestMatchStickDrawer testMatchStickDrawer;
    private String figPath;
    private GaussianNoiseMapper noiseMapper;

    @Before
    public void setUp() throws Exception {
        testMatchStickDrawer = new TestMatchStickDrawer();
        testMatchStickDrawer.setup(500, 500);

        noiseMapper = new GaussianNoiseMapper();
        noiseMapper.setBackground(0);
        noiseMapper.setWidth(500);
        noiseMapper.setHeight(500);

        baseMStick = new TwoByTwoMatchStick(noiseMapper);
        baseMStick.setMaxAttempts(-1);
        baseMStick.setProperties(8, "SHADE", 1.0);
        baseMStick.genMatchStickRand();

        figPath = "/home/r2_allen/Pictures";


    }

    @Test
    public void test_partially_inside(){

        EStimShapeTwoByTwoMatchStick firstMStick = new EStimShapeTwoByTwoMatchStick(RFStrategy.PARTIALLY_INSIDE, PARTIAL_RF, noiseMapper);
        double maxSizeDiameterDegrees = 1.5;
        firstMStick.setProperties(maxSizeDiameterDegrees, "SHADE", 1.0);
        firstMStick.genMatchStickFromComponent(baseMStick, Collections.singletonList(1), 2, firstMStick.maxAttempts);
        testMatchStickDrawer.drawMStick(firstMStick);
        testMatchStickDrawer.drawCompMap(firstMStick);
        testMatchStickDrawer.saveImage(figPath + "/firstMStick");
        testMatchStickDrawer.clear();


        EStimShapeTwoByTwoMatchStick secondMStick = new EStimShapeTwoByTwoMatchStick(RFStrategy.PARTIALLY_INSIDE, PARTIAL_RF, noiseMapper);
        secondMStick.setProperties(maxSizeDiameterDegrees, "SHADE", 1.0);
        secondMStick.genMorphedBaseMatchStick(firstMStick, 1, secondMStick.maxAttempts, true, true);
        testMatchStickDrawer.drawMStick(secondMStick);
        testMatchStickDrawer.drawCompMap(secondMStick);
        testMatchStickDrawer.saveImage(figPath + "/secondMStick");
        testMatchStickDrawer.clear();

        EStimShapeTwoByTwoMatchStick thirdMStick = new EStimShapeTwoByTwoMatchStick(RFStrategy.PARTIALLY_INSIDE, PARTIAL_RF, noiseMapper);
        thirdMStick.setProperties(maxSizeDiameterDegrees, "SHADE", 1.0);
        thirdMStick.genMorphedDrivingComponentMatchStick(firstMStick, 0.5, 0.5, true, true, firstMStick.maxAttempts);
        testMatchStickDrawer.drawMStick(thirdMStick);
        testMatchStickDrawer.drawCompMap(thirdMStick);
        testMatchStickDrawer.saveImage(figPath + "/thirdMStick");
        testMatchStickDrawer.clear();

        EStimShapeTwoByTwoMatchStick fourthMStick = new EStimShapeTwoByTwoMatchStick(RFStrategy.PARTIALLY_INSIDE, PARTIAL_RF, noiseMapper);
        fourthMStick.setProperties(maxSizeDiameterDegrees, "SHADE", 1.0);
        fourthMStick.genSwappedBaseAndDrivingComponentMatchStick(secondMStick, 1, thirdMStick, true, 15);
        testMatchStickDrawer.drawMStick(fourthMStick);
        testMatchStickDrawer.drawCompMap(fourthMStick);
        testMatchStickDrawer.saveImage(figPath + "/fourthMStick");
        testMatchStickDrawer.clear();


    }
}