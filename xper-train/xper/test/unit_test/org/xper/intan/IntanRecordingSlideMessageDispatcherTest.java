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
public class IntanRecordingSlideMessageDispatcherTest {

    private static IntanRecordingSlideMessageDispatcher intanRecordingSlideMessageDispatcher;
    private static IntanClient intanClient;

    @BeforeClass
    public static void set_up(){
        FileUtil.loadTestSystemProperties("/xper.properties.test");
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(FileUtil.loadConfigClass("test.experiment.config_class"));
        intanRecordingSlideMessageDispatcher = context.getBean(IntanRecordingSlideMessageDispatcher.class);
        intanClient = context.getBean(IntanClient.class);
    }

    @Test
    public void do_not_crash_when_intan_not_connected(){
        intanRecordingSlideMessageDispatcher.experimentStop(0); //disconnects Intan

        intanRecordingSlideMessageDispatcher.slideOn(0, 0, 1);
        intanRecordingSlideMessageDispatcher.slideOff(0, 0, 0, 1);

        intanRecordingSlideMessageDispatcher.experimentStart(0);
    }

    @Test
    public void trial_init_renames_base_filename_to_taskId(){
        intanRecordingSlideMessageDispatcher.experimentStart(0);
        intanRecordingSlideMessageDispatcher.slideOn(0, 0, 1);
        intanRecordingSlideMessageDispatcher.slideOff(0, 0, 0, 1);
        ThreadUtil.sleep(500);
        intanRecordingSlideMessageDispatcher.experimentStop(0);
        assertTrue(intanClient.get("Filename.BaseFilename").equals("1"));
    }

    /**
     * Quickly run three trials to test file saving.
     */
    @Ignore
    @Test
    public void run_multiple_trials(){
        intanRecordingSlideMessageDispatcher.experimentStart(0);

        intanRecordingSlideMessageDispatcher.slideOn(0, 0, 1);
        intanRecordingSlideMessageDispatcher.slideOff(0, 0, 0, 1);
        ThreadUtil.sleep(500);


        intanRecordingSlideMessageDispatcher.slideOn(0, 0, 2);
        intanRecordingSlideMessageDispatcher.slideOff(0, 0, 0, 2);
        ThreadUtil.sleep(500);

        intanRecordingSlideMessageDispatcher.slideOn(0, 0, 3);
        intanRecordingSlideMessageDispatcher.slideOff(0, 0, 0, 3);
        ThreadUtil.sleep(500);

        intanRecordingSlideMessageDispatcher.experimentStop(0);
    }
}