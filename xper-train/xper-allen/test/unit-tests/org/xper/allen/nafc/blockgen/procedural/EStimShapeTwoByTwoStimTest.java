package org.xper.allen.nafc.blockgen.procedural;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.app.procedural.EStimExperimentTrialGenerator;
import org.xper.allen.drawing.ga.TestMatchStickDrawer;
import org.xper.util.FileUtil;

public class EStimShapeTwoByTwoStimTest {

    private EStimExperimentTrialGenerator generator;
    private TestMatchStickDrawer testMatchStickDrawer;
    private String figPath;

    @Before
    public void setUp() throws Exception {

        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));


        generator = context.getBean(EStimExperimentTrialGenerator.class);

        testMatchStickDrawer = new TestMatchStickDrawer();
        testMatchStickDrawer.setup(500, 500);

        figPath = "/home/r2_allen/Pictures";
    }

    @Test
    public void test_two_by_two_stim(){


    }
}