package org.xper.allen.pga.alexnet;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.drawing.RGBColor;
import org.xper.util.FileUtil;

import java.util.ArrayList;

public class GrowingStimTest {

    private JavaConfigApplicationContext context;
    private FromDbAlexNetGABlockGenerator generator;
    private AlexNetDrawingManager alexNetDrawingManager;

    @Before
    public void setUp() throws Exception {
        FileUtil.loadTestSystemProperties("/xper.properties.alexnet");
        context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));
        generator = context.getBean(FromDbAlexNetGABlockGenerator.class);

        generator.getDrawingManager().createDrawerWindow();
    }

    @Test
    public void testLoadingFromSpec(){
        SeedingStim seedingStim = new SeedingStim(generator,  0L, 3L,
                "SHADE",
                new RGBColor(1f,0f,0f),
                new float[]{0.0f, 354.0f, 354.0f, 1.0f});

        AlexNetGAMatchStick original = seedingStim.createMStick();
        AllenMStickSpec spec = AlexNetGAStim.createMStickSpec(original);
        AlexNetGAMStickData originalData = original.getMStickData();

        AlexNetGAMatchStick loadedMStick = new AlexNetGAMatchStick( new float[]{0.0f, 354.0f, 354.0f, 1.0f},
                new RGBColor(1.0, 0, 0),
                originalData.location,
                originalData.sizeDiameter,
                "SHADE");

        loadedMStick.genMatchStickFromShapeSpec(spec, new double[]{0,0,0});
        loadedMStick.positionShape();
        generator.drawingManager.createAndSavePNG(original, 3L, new ArrayList<>(), "/home/r2_allen/git/EStimShape/xper-train/xper-allen/test/test-resources/testBin");
        generator.drawingManager.createAndSavePNG(loadedMStick, 4L, new ArrayList<>(), "/home/r2_allen/git/EStimShape/xper-train/xper-allen/test/test-resources/testBin");
    }

    @Test
    public void testRFLocStim(){
        /**
         * Should be able to create a SeedingStim and then create a RFLocStim from it
         * The RFLocStim should have a location and size that is different from the SeedingStim
         * magnitude controls how different size and location are and should be between 0 and 1
         * 0 means no change, 1 means maximum change
         *
         * There's always a 50/50 chance of changing size or location
         * If size is changed, location has a magnitude chance of being changed as well
         * If location is changed, size has a magnitude chance of being changed as well
         *
         */
        SeedingStim seedingStim = new SeedingStim(generator,  0L, 1L,
                "SHADE",
                new RGBColor(1f,0f,0f),
                new float[]{0.0f, 354.0f, 354.0f, 1.0f});

        seedingStim.writeStim();
        System.out.println("Pre Size Diameter: " + seedingStim.sizeDiameter);
        System.out.println("Pre Location: " + seedingStim.location.getX() + ", " + seedingStim.location.getY());

        RFLocStim rfLocStim = new RFLocStim(generator, 1L, 2L,
                "SHADE",
                new RGBColor(1f,0f,0f),
                new float[]{0.0f, 354.0f, 354.0f, 1.0f},
                1.0
                );

        rfLocStim.writeStim();
        System.out.println("Post Size Diameter: " + rfLocStim.sizeDiameter);
        System.out.println("Post Location: " + rfLocStim.location.getX() + ", " + rfLocStim.location.getY());
    }

    @Test
    public void testGrowingStim(){
        SeedingStim seedingStim = new SeedingStim(generator,  0L, 1L,
                "SHADE",
                new RGBColor(1f,0f,0f),
                new float[]{0.0f, 354.0f, 354.0f, 1.0f});

        seedingStim.writeStim();
        System.out.println(seedingStim.sizeDiameter);

        GrowingStim growingStim = new GrowingStim(generator, 1L, 2L,
                "SHADE",
                new RGBColor(1f,0f,0f),
                new float[]{0.0f, 354.0f, 354.0f, 1.0f},
                0.75
                );

        growingStim.writeStim();
        System.out.println(growingStim.sizeDiameter);
    }


}