package org.xper.allen.pga;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.util.FileUtil;

import static org.junit.Assert.*;

public class FromDbGABlockGeneratorTest {

    private FromDbGABlockGenerator generator;

    @Before
    public void setUp() throws Exception {
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));

        MultiGaDbUtil dbUtil = context.getBean(MultiGaDbUtil.class);

        generator = new FromDbGABlockGenerator();
        generator.setDbUtil(dbUtil);
        generator.setNumTrialsPerStimulus(5);
    }

    @Test
    public void addTrials() {
        generator.addTrials();
        System.out.println(generator.getStims().get(0));
    }
}