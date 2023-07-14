package org.xper.drawing;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.app.experiment.Console;
import org.xper.app.experiment.Experiment;
import org.xper.classic.MarkEveryStepTrialDrawingController;
import org.xper.classic.MarkStimTrialDrawingController;
import org.xper.classic.TrialDrawingController;
import org.xper.classic.vo.TrialContext;
import org.xper.console.ExperimentConsole;
import org.xper.experiment.ExperimentRunner;
import org.xper.util.FileUtil;
import org.xper.util.ThreadUtil;

public class MarkerTest {

    private TrialDrawingController drawingController;
    private JavaConfigApplicationContext context;

    @Before
    public void setUp() throws Exception {
        context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));

        drawingController = context.getBean(TrialDrawingController.class);
    }

    @Test
    public void run_exp(){
        context.getBean(ExperimentConsole.class).run();
        context.getBean(ExperimentRunner.class).run();
    }

    @Test
    public void draw_marker() {
        drawingController.init();
        drawingController.trialStart(new TrialContext());
//        drawingController.fixationOn(new TrialContext());

        ThreadUtil.sleep(100000);

    }
}