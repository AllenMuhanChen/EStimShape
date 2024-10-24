package org.xper.allen.pga.alexnet;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
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