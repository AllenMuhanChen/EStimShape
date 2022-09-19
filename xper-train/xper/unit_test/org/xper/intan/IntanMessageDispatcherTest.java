package org.xper.intan;

import org.junit.BeforeClass;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.classic.vo.TrialContext;
import org.xper.util.FileUtil;

/**
 * @author Allen Chen
 *
 * Run these tests without Intan running / listening for connections.
 *
 */
public class IntanMessageDispatcherTest {

    private static IntanMessageDispatcher intanMessageDispatcher;

    @BeforeClass
    public static void set_up(){
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(FileUtil.loadConfigClass("test.experiment.config_class"));
        intanMessageDispatcher = context.getBean(IntanMessageDispatcher.class);
    }

    @Test
    public void do_not_crash_when_intan_not_connected(){
        intanMessageDispatcher.experimentStop(0);
        intanMessageDispatcher.trialInit(0, new TrialContext());
        intanMessageDispatcher.trialStop(0, new TrialContext());
        intanMessageDispatcher.experimentStart(0);
    }
}
