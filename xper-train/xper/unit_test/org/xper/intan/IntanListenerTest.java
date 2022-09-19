package org.xper.intan;

import org.junit.BeforeClass;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.classic.vo.TrialContext;
import org.xper.time.TestingTimeUtil;
import org.xper.util.FileUtil;

/**
 * @author Allen Chen
 *
 * Run these tests without Intan running / listening for connections.
 *
 * This class tests the case that Intan is enabled in the configs, but there is no running
 * intan present to record.
 *
 * that is, there should be no crashes
 */
public class IntanListenerTest {

    private static IntanEventListener intanEventListener;

    @BeforeClass
    public static void set_up(){
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(FileUtil.loadConfigClass("test.experiment.config_class"));
        intanEventListener = context.getBean(IntanEventListener.class);
    }

    @Test
    public void do_not_crash_when_intan_not_connected(){
        intanEventListener.experimentStop(0);
        intanEventListener.trialInit(0, new TrialContext());
        intanEventListener.trialStop(0, new TrialContext());
        intanEventListener.experimentStart(0);
    }
}
