package org.xper.fixtrain;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.experiment.ExperimentTask;
import org.xper.experiment.TaskDataSource;
import org.xper.fixtrain.console.FixTrainClient;
import org.xper.util.FileUtil;
import org.xper.util.ThreadUtil;

import static org.junit.Assert.*;
import static org.xper.fixtrain.FixTrainTest.loadTestSystemProperties;

public class FixTrainTaskDataSourceTest {

    private JavaConfigApplicationContext context;

    @Before
    public void setUp() throws Exception {
        loadTestSystemProperties("/xper.properties.fixtrain");

        context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("fixcal.config_class", FixTrainConfig.class));

    }

    @Test
    public void tcp_client_sends_stim_and_xfm_specs_to_data_source_server(){
        FixTrainTaskDataSource dataSource = (FixTrainTaskDataSource) context.getBean(TaskDataSource.class, "taskDataSource");
        FixTrainClient client = context.getBean(FixTrainClient.class);

        dataSource.start();
        client.changeStim("test_stim");
        client.changeXfm("test_xfm");
        ThreadUtil.sleep(100);

        ExperimentTask task = dataSource.getNextTask();
        assertEquals("test_xfm", task.getXfmSpec());
        assertEquals("test_stim", task.getStimSpec());
    }
}