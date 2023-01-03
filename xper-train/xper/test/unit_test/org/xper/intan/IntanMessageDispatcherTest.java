package org.xper.intan;

import org.junit.After;
import org.junit.BeforeClass;
import org.junit.Ignore;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.classic.vo.TrialContext;
import org.xper.experiment.ExperimentTask;
import org.xper.util.FileUtil;
import org.xper.util.ThreadUtil;

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
        FileUtil.loadTestSystemProperties("/xper.properties.test");
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(FileUtil.loadConfigClass("test.experiment.config_class"));
        intanMessageDispatcher = context.getBean(IntanMessageDispatcher.class);
        intanClient = context.getBean(IntanClient.class);
    }

    @Test
    public void do_not_crash_when_intan_not_connected(){
        intanMessageDispatcher.experimentStop(0); //disconnects Intan

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

    /**
     * Quickly run three trials to test file saving.
     */
    @Ignore
    @Test
    public void run_multiple_trials(){
        TrialContext testContext = new TrialContext();
        ExperimentTask testTask = new ExperimentTask();
        testTask.setTaskId(1);
        testContext.setCurrentTask(testTask);

        intanMessageDispatcher.experimentStart(0);

        intanMessageDispatcher.trialInit(0, testContext);
        intanMessageDispatcher.trialStop(0, testContext);
        ThreadUtil.sleep(500);

        testTask.setTaskId(2);
        testContext.setCurrentTask(testTask);
        intanMessageDispatcher.trialInit(0, testContext);
        intanMessageDispatcher.trialStop(0, testContext);
        ThreadUtil.sleep(500);

        testTask.setTaskId(3);
        testContext.setCurrentTask(testTask);
        intanMessageDispatcher.trialInit(0, testContext);
        intanMessageDispatcher.trialStop(0, testContext);
        ThreadUtil.sleep(500);

        intanMessageDispatcher.experimentStop(0);
    }
}
