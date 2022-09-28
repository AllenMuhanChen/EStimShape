package org.xper.rfplot;

import org.junit.BeforeClass;
import org.junit.Ignore;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.app.rfplot.RFPlotExperiment;
import org.xper.console.ExperimentConsole;
import org.xper.console.IConsolePlugin;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.exception.XGLException;
import org.xper.experiment.Experiment;
import org.xper.rfplot.drawing.RFPlotDrawable;
import org.xper.rfplot.drawing.RFPlotGaborObject;
import org.xper.rfplot.drawing.RFPlotPngObject;
import org.xper.rfplot.gui.RFPlotConsolePlugin;
import org.xper.util.FileUtil;
import org.xper.util.ThreadUtil;
import sun.awt.ExtendedKeyCodes;

import javax.swing.*;
import java.awt.*;
import java.awt.event.InputEvent;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.LinkedList;

import static org.junit.Assert.assertEquals;

public class RFPlotConsolePluginTest {

    private static RFPlotConsolePlugin plugin;
    private static MockRFPlotTaskDataSourceClient client;
    private static LinkedHashMap<String, RFPlotDrawable> rfObjectMap;
    private static ExperimentConsole console;
    private static JavaConfigApplicationContext context;
    private Robot bot;

    @BeforeClass
    public static void setUp(){
        context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("rfplot.config_class", RFPlotConfig.class));

        plugin = context.getBean(RFPlotConsolePlugin.class);

    }

    public static void startConsole(){

        try {
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
        } catch (Exception e) {
            throw new XGLException(e);
        }

        console = context.getBean(ExperimentConsole.class);
        console.run();
    }

    public void startExperiment(){
        Thread t = new Thread(new Runnable() {
            @Override
            public void run() {
                RFPlotExperiment.main(new String[]{""});
            }
        });
        t.start();
    }


    @Test
    public void start(){
        try {
            bot = new Robot();
        } catch (AWTException e) {
            throw new RuntimeException(e);
        }
//        startExperiment();
        startConsole();

        ThreadUtil.sleep(1000);
        keyPress('p');
        moveMouseToMiddle();
        keyPress('r');
        ThreadUtil.sleep(500);
        keyPress('d');
        keyPress('d');
        keyPress('d');
        keyPress('d');
        moveMouseTo(0.2,0.2);



        ThreadUtil.sleep(100000);
    }

    private void moveMouseTo(double x, double y) {
        Point locationOnScreen = console.getConsoleCanvas().getLocationOnScreen();
        int vpWidth = console.getConsoleRenderer().getRenderer().getVpWidth();
        int vpHeight = console.getConsoleRenderer().getRenderer().getVpHeight();
        bot.mouseMove((int) (x*(locationOnScreen.getX()+vpWidth)), (int) (y*(locationOnScreen.getY()+vpHeight/2)));
    }

    private void moveMouseToMiddle() {
        Point locationOnScreen = console.getConsoleCanvas().getLocationOnScreen();
        int vpWidth = console.getConsoleRenderer().getRenderer().getVpWidth();
        int vpHeight = console.getConsoleRenderer().getRenderer().getVpHeight();
        bot.mouseMove((int) locationOnScreen.getX()+vpWidth/2, (int) locationOnScreen.getY()+vpHeight/2);
    }

    private void keyPress(char toPress) {
        bot.keyPress(ExtendedKeyCodes.getExtendedKeyCodeForChar(toPress));
        bot.keyRelease(ExtendedKeyCodes.getExtendedKeyCodeForChar(toPress));
    }

    private void click(JComponent component){
        bot.mouseMove(component.getLocationOnScreen().x, component.getLocationOnScreen().y);
        bot.mousePress(InputEvent.BUTTON1_MASK);
        try{Thread.sleep(250);}catch(InterruptedException e){}
        bot.mouseRelease(InputEvent.BUTTON1_MASK);
    }

    @Ignore
    @Test
    public void start_plugin_sets_default_stim_spec_and_xfm(){
        plugin.startPlugin();

        String actualStimSpec = client.getMockStim();
        String expectedStimSpec = new RFPlotGaborObject().getSpec();

        String actualXfmSpec = client.getMockXfm();
        String expectedXfmSpec = new RFPlotXfmSpec().fromXml(null).toXml();

        assertEquals(expectedStimSpec, actualStimSpec);
        assertEquals(expectedXfmSpec, actualXfmSpec);
    }

    @Ignore
    @Test
    public void mouse_move_changes_location(){
        plugin.handleMouseMove(50,50);

        String xfm = client.getMockXfm();
        RFPlotXfmSpec spec = RFPlotXfmSpec.fromXml(xfm);
        Coordinates2D actualCoords = spec.getTranslation();
        Coordinates2D expectedCoords = new Coordinates2D(50,50);

        assertEquals(expectedCoords, actualCoords);
    }
}
