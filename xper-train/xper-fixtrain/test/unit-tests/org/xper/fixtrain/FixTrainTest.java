package org.xper.fixtrain;

import org.junit.Before;
import org.junit.Ignore;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.XperConfig;
import org.xper.console.ExperimentConsole;
import org.xper.exception.ExperimentSetupException;
import org.xper.experiment.ExperimentRunner;
import org.xper.util.DbUtil;
import org.xper.util.FileUtil;
import org.xper.util.ThreadUtil;

import java.util.Properties;

public class FixTrainTest {

    private JavaConfigApplicationContext context;

    @Before
    public void setUp() throws Exception {
        context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("fixcal.config_class", FixTrainConfig.class));
        DbUtil dbUtil = context.getBean(DbUtil.class);
        System.out.println(dbUtil.toString());
    }

    @Test
    @Ignore
    public void main() {
        ExperimentConsole console = context.getBean(ExperimentConsole.class);
        console.run();


        ExperimentRunner runner = context.getBean(ExperimentRunner.class);
        runner.run();
        ThreadUtil.sleep(1000000);
    }

}