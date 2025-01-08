package org.xper.allen.drawing.mstickbubbles;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;
import org.xper.drawing.TestDrawingWindow;
import org.xper.util.ResourceUtil;
import org.xper.util.ThreadUtil;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.File;
import java.nio.file.Paths;
import java.util.Arrays;
import java.util.HashSet;

import static org.xper.allen.drawing.ga.GAMatchStickTest.COMPLETE_RF;
import static org.xper.allen.drawing.ga.GAMatchStickTest.PARTIAL_RF;

public class MStickBubbleGeneratorTest {

    private TestDrawingWindow window;
    private ReceptiveField receptiveField;
    public final static String FILE_NAME = Paths.get(ResourceUtil.getResource("testBin"), "MStickBubble_testFile").toString();;
    private AllenMatchStick matchStick;

    @Before
    public void setUp() throws Exception {
        window = TestDrawingWindow.createDrawerWindow(1000, 1000);

        String stimType = "Seeding";
        RFStrategy rfStrategy = RFStrategy.PARTIALLY_INSIDE;

        if (rfStrategy == RFStrategy.COMPLETELY_INSIDE){
            receptiveField = COMPLETE_RF;
        } else {
            receptiveField = PARTIAL_RF;
        }

        GAMatchStick parentStick = new GAMatchStick(receptiveField, rfStrategy);
        parentStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, 2), "SHADE");
        parentStick.genMatchStickRand();
        AllenMStickSpec parentSpec = new AllenMStickSpec();
        parentSpec.setMStickInfo(parentStick, true);
        parentSpec.writeInfo2File(FILE_NAME);

        switch (stimType){
            case "Seeding":
                matchStick = new GAMatchStick(receptiveField, rfStrategy);
                matchStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, 1.5), "SHADE");
                matchStick.genMatchStickRand();
                break;
            case "Zooming":
                matchStick = new GAMatchStick(PARTIAL_RF, RFStrategy.PARTIALLY_INSIDE);
                matchStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, 1.5), "SHADE");
                ((GAMatchStick) matchStick).genPartialFromFile(FILE_NAME + "_spec.xml", 1);
                break;
            case "Growing":
                matchStick = new GrowingMatchStick(receptiveField, 1/3.0, rfStrategy, "SHADE");
                matchStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, 1.5), "SHADE");
                ((GrowingMatchStick) matchStick).genGrowingMatchStick(parentStick, 0.5);
                break;
            case "AddLimbs":
                matchStick = new GAMatchStick(receptiveField, rfStrategy);
                matchStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, 1.5), "SHADE");
                ((GrowingMatchStick) matchStick).genAddedLimbsMatchStick(parentStick, 1);
                break;
            case "RemoveLimbs":
                matchStick = new GAMatchStick(receptiveField, rfStrategy);
                matchStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, 1.5), "SHADE");
                ((GrowingMatchStick) matchStick).genRemovedLimbsMatchStick(parentStick, new HashSet<>(Arrays.asList(1)));
                break;
            case "Rand":
                matchStick = new AllenMatchStick();
                matchStick.setProperties(5, "SHADE");
                matchStick.genMatchStickRand();
        }

    }
    @Test
    public void generateBubblePixels() {
        MStickBubbleGenerator mStickBubbleGenerator = new MStickBubbleGenerator();
        mStickBubbleGenerator.renderer = window.renderer;
        BufferedImage bubbleMap = null;
        try {
            bubbleMap = mStickBubbleGenerator.generateBubbleMap(matchStick, 5);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }

        File outputFile = Paths.get(ResourceUtil.getResource("testBin"), "MStickBubbleBubbleMap_testFile.png").toFile();
        try {
            ImageIO.write(bubbleMap, "png", outputFile);
        } catch (Exception e) {
            e.printStackTrace();
        }

        // Draw the original matchstick
        window.draw(matchStick);
        File outputFile2 = Paths.get(ResourceUtil.getResource("testBin"), "MStickBubbleBubbleMap_testFile2").toFile();
        AllenPNGMaker.saveImage(outputFile2.getName(), window.renderer.getVpWidth(), window.renderer.getVpHeight(), outputFile2.getParentFile().getAbsolutePath());

        ThreadUtil.sleep(100000);
    }
    @After
    public void tearDown() throws Exception {
        window.close();
    }
}