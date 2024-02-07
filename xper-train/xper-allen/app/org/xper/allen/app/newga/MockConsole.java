package org.xper.allen.app.newga;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.console.ExperimentConsole;
import org.xper.exception.XGLException;
import org.xper.util.FileUtil;
import org.xper.util.ThreadUtil;

import javax.swing.*;

public class MockConsole {
    public static void main(String[] args) {
        FileUtil.loadTestSystemProperties("/xper.properties.pga.mock");
        try {
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
        } catch (Exception e) {
            throw new XGLException(e);
        }
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));
        ExperimentConsole console = context.getBean(ExperimentConsole.class);
        console.run();
        ThreadUtil.sleep(1000);
        console.pauseResume();
    }
}