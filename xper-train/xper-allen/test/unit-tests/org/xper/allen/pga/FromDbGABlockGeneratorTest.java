package org.xper.allen.pga;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.app.GAConsole;
import org.xper.allen.app.GAExperiment;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.util.FileUtil;

import static org.junit.Assert.*;

public class FromDbGABlockGeneratorTest {

    private FromDbGABlockGenerator generator;
    private final String[] emptyArgs = {""};
    @Before
    public void setUp() throws Exception {
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));


        generator = context.getBean(FromDbGABlockGenerator.class);
    }

    @Test
    public void runExp(){
        GAConsole.main(emptyArgs);
        GAExperiment.main(emptyArgs);
    }

    @Test
    public void run() {
        generator.generate();
    }
}