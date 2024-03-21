package org.xper.allen.app.monitorlinearization;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.monitorlinearization.MonLinConfig;
import org.xper.allen.monitorlinearization.MonLinTrialGenerator;
import org.xper.util.FileUtil;

public class MonLinGenerator {

    public static void main(String[] args) {
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(FileUtil.loadConfigClass("experiment.config_class"), MonLinConfig.class);
        MonLinTrialGenerator gen = context.getBean(MonLinTrialGenerator.class);
        if (args[0].equals("Isoluminant")){
            gen.mode = "Isoluminant";
        } else if (args[0].equals("Linear")){
            gen.mode = "Linear";
        } else if (args[0].equals("RedGreenSinusoidal")){
            gen.mode = "RedGreenSinusoidal";
        } else if (args[0].equals("LinearRepeats")){
            gen.mode = "LinearRepeats";
        } else if (args[0].equals("RedGreenSinusoidalLargeSpan")){
            gen.mode = "RedGreenSinusoidalLargeSpan";
        } else if (args[0].equals("TestIsoluminant")){
            gen.mode = "TestIsoluminant";
        }

        gen.generate();
    }
}