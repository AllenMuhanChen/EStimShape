package org.xper.allen.app.newga;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.newga.blockgen.SlotGABlockGenerator;
import org.xper.allen.pga.FromDbGABlockGenerator;
import org.xper.util.FileUtil;

public class MockNewGATrialGenerator {

    public static void main(String[] args) {
        FileUtil.loadTestSystemProperties("/xper.properties.pga.mock");
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));
        FromDbGABlockGenerator generator = context.getBean(FromDbGABlockGenerator.class);

        generator.generate();
    }
}