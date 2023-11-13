package org.xper.allen.nafc.blockgen.procedural;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.procedural.ProceduralStim.ProceduralStimParameters;
import org.xper.util.FileUtil;

import java.awt.*;

import static org.junit.Assert.*;

public class ProceduralStimTest {

    private ProceduralExperimentBlockGen generator;
    private ProceduralMatchStick baseMStick;

    @Before
    public void setUp() throws Exception {
        FileUtil.loadTestSystemProperties("/xper.properties.procedural");

        JavaConfigApplicationContext context = new JavaConfigApplicationContext(FileUtil.loadConfigClass("experiment.config_class"));

        generator = context.getBean(ProceduralExperimentBlockGen.class);
        baseMStick = new ProceduralMatchStick();
        baseMStick.setProperties(generator.getMaxImageDimensionDegrees());
        baseMStick.genMatchStickRand();
    }

    @Test
    public void writeStim() {
        ProceduralStimParameters parameters = new ProceduralStimParameters(
                new Lims(0, 0),
                new Lims(0, 0),
                8,
                10,
                0.5,
                3,
                2,
                0.5,
                new Color(1,1,1)
                );

        ProceduralStim stim = new ProceduralStim(generator, parameters, baseMStick, 1);
        stim.writeStim();
    }
}