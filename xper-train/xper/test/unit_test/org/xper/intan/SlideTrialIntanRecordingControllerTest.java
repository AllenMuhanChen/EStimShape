package org.xper.intan;

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
public class SlideTrialIntanRecordingControllerTest {

    private static SlideTrialIntanRecordingController slideTrialIntanRecordingController;
    private static IntanClient intanClient;

    @BeforeClass
    public static void set_up(){
        FileUtil.loadTestSystemProperties("/xper.properties.test");
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(FileUtil.loadConfigClass("test.experiment.config_class"));
        slideTrialIntanRecordingController = context.getBean(SlideTrialIntanRecordingController.class);
        intanClient = context.getBean(IntanClient.class);
    }

    @Test
    public void do_not_crash_when_intan_not_connected(){
        slideTrialIntanRecordingController.experimentStop(0); //disconnects Intan

        slideTrialIntanRecordingController.trialInit(0, new TrialContext());
        slideTrialIntanRecordingController.trialStop(0, new TrialContext());

        slideTrialIntanRecordingController.experimentStart(0);
    }

    @Test
    public void trial_init_renames_base_filename_to_taskId(){
        TrialContext testContext = new TrialContext();
        ExperimentTask testTask = new ExperimentTask();
        testTask.setTaskId(1);
        testContext.setCurrentTask(testTask);

        slideTrialIntanRecordingController.experimentStart(0);
        slideTrialIntanRecordingController.trialInit(0, testContext);
        slideTrialIntanRecordingController.trialStop(0, testContext);
        assertTrue(intanClient.get("Filename.BaseFilename").equals("1"));
        slideTrialIntanRecordingController.experimentStop(0);
    }

    @Ignore
    @Test
    public void slide_writes_taskId_to_live_notes(){
        TrialContext testContext = new TrialContext();
        ExperimentTask testTask = new ExperimentTask();
        testTask.setTaskId(1);
        testContext.setCurrentTask(testTask);

        slideTrialIntanRecordingController.experimentStart(0);
        slideTrialIntanRecordingController.trialInit(0, testContext);
        slideTrialIntanRecordingController.slideOn(0, 0, 1);
        slideTrialIntanRecordingController.trialStop(0, testContext);
        slideTrialIntanRecordingController.experimentStop(0);

        //Now manually go see if the livesnotes txt file was created on the Intan Machine.
    }


    @Ignore
    @Test
    public void run_multiple_trials(){
        TrialContext testContext = new TrialContext();
        ExperimentTask testTask = new ExperimentTask();
        testTask.setTaskId(1);
        testContext.setCurrentTask(testTask);

        slideTrialIntanRecordingController.experimentStart(0);

        slideTrialIntanRecordingController.trialInit(0, testContext);
        slideTrialIntanRecordingController.trialStop(0, testContext);
        ThreadUtil.sleep(500);

        testTask.setTaskId(2);
        testContext.setCurrentTask(testTask);
        slideTrialIntanRecordingController.trialInit(0, testContext);
        slideTrialIntanRecordingController.trialStop(0, testContext);
        ThreadUtil.sleep(500);

        testTask.setTaskId(3);
        testContext.setCurrentTask(testTask);
        slideTrialIntanRecordingController.trialInit(0, testContext);
        slideTrialIntanRecordingController.trialStop(0, testContext);
        ThreadUtil.sleep(500);

        slideTrialIntanRecordingController.experimentStop(0);

        //Now manually go see if these files were created on the Intan Machine.
    }
}