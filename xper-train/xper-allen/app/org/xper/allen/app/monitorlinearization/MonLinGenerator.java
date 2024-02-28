package org.xper.allen.app.monitorlinearization;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.monitorlinearization.MonLinConfig;
import org.xper.allen.monitorlinearization.MonLinTrialGenerator;
import org.xper.util.FileUtil;

public class MonLinGenerator {
    public static void main(String[] args) {
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(FileUtil.loadConfigClass("experiment.config_class"), MonLinConfig.class);
        MonLinTrialGenerator gen = context.getBean(MonLinTrialGenerator.class);
        gen.generate();
    }
}