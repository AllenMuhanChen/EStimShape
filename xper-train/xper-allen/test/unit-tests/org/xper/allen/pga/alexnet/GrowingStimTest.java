package org.xper.allen.pga.alexnet;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.drawing.Coordinates2D;
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
    public void testGrowingStim(){
        SeedingStim seedingStim = new SeedingStim(generator,  0L, 1L,
                "SHADE",
                new RGBColor(1f,0f,0f),
                new float[]{0.0f, 354.0f, 354.0f, 1.0f});

        seedingStim.writeStim();


        GrowingStim growingStim = new GrowingStim(generator, 1L, 2L,
                "SHADE",
                new RGBColor(1f,0f,0f),
                seedingStim.location,
                new float[]{0.0f, 354.0f, 354.0f, 1.0f},
                seedingStim.sizeDiameter,
                0.5
                );

        growingStim.writeStim();

    }


}