package org.xper.allen.app.newga;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.newga.blockgen.SlotGABlockGenerator;
import org.xper.util.FileUtil;

public class MockNewGATrialGenerator {

    public static void main(String[] args) {
        FileUtil.loadTestSystemProperties("/xper.properties.newga.mock");
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));
        SlotGABlockGenerator generator = context.getBean(SlotGABlockGenerator.class);

        generator.generate();
    }
}