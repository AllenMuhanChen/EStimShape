package org.xper.intan;

import org.junit.After;
import org.junit.BeforeClass;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.classic.vo.TrialContext;
import org.xper.experiment.ExperimentTask;
import org.xper.util.FileUtil;

import static org.junit.Assert.assertTrue;

/**
 * @author Allen Chen
 *
 */
public class IntanMessageDispatcherTest {

    private static IntanMessageDispatcher intanMessageDispatcher;
    private static IntanClient intanClient;

    @BeforeClass
    public static void set_up(){
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(FileUtil.loadConfigClass("test.experiment.config_class"));
        intanMessageDispatcher = context.getBean(IntanMessageDispatcher.class);
        intanClient = context.getBean(IntanClient.class);
    }

    /**
     * Run this test with intan disconnected
     */
    @Test
    public void do_not_crash_when_intan_not_connected(){
        intanMessageDispatcher.experimentStop(0);
        intanMessageDispatcher.trialInit(0, new TrialContext());
        intanMessageDispatcher.trialStop(0, new TrialContext());
        intanMessageDispatcher.experimentStart(0);
    }

    @Test
    public void trial_init_renames_base_filename_to_taskId(){
        TrialContext testContext = new TrialContext();
        ExperimentTask testTask = new ExperimentTask();
        testTask.setTaskId(1);
        testContext.setCurrentTask(testTask);

        intanMessageDispatcher.experimentStart(0);
        intanMessageDispatcher.trialInit(0, testContext);
        intanMessageDispatcher.trialStop(0, testContext);

        assertTrue(intanClient.get("Filename.BaseFilename").equals("1"));
    }
}
