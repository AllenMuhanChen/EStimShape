package org.xper.rfplot;

import org.junit.BeforeClass;
import org.junit.Test;
import org.xper.rfplot.gui.RFPlotGUIController;
import org.xper.rfplot.gui.RFPlotGUITestView;
import org.xper.rfplot.gui.RFPlotGuiModel;
import org.xper.util.ThreadUtil;
import sun.awt.ExtendedKeyCodes;

import javax.swing.*;
import java.awt.*;
import java.awt.event.InputEvent;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public class RFPlotGUITest {

    private static RFPlotGUITestView view;
    private static RFPlotGuiModel model;
    private static RFPlotGUIController controller;
    private static MockRFPlotTaskDataSourceClient client;
    private static Robot bot;

    public static void main(String[] args) {
        setUp();
    }

    @BeforeClass
    public static void setUp(){
        client = new MockRFPlotTaskDataSourceClient();
        model = new RFPlotGuiModel();
        model.setClient(client);
        view = new RFPlotGUITestView();
        controller = new RFPlotGUIController();
        controller.setModel(model);
        controller.setView(view);
        controller.initController();
        try {
            bot = new Robot();
        } catch (AWTException e) {
            throw new RuntimeException(e);
        }
    }

    @Test
    public void save_button() throws AWTException {
        click(view.getStimTextField());
        keyPress('h');
        keyPress('e');
        keyPress('l');
        keyPress('l');
        keyPress('o');
        click(view.getXfmTextField());
        keyPress('w');
        keyPress('o');
        keyPress('r');
        keyPress('l');
        keyPress('d');
        click(view.getSaveButton());
        ThreadUtil.sleep(100); //save requires time from GUI
        assertEquals("hello", client.getMockStim());
        assertEquals("world", client.getMockXfm());
    }

    private void keyPress(char toPress) throws AWTException {
        bot.keyPress(ExtendedKeyCodes.getExtendedKeyCodeForChar(toPress));
        bot.keyRelease(ExtendedKeyCodes.getExtendedKeyCodeForChar(toPress));
    }

    private void click(JComponent component) throws AWTException {
        bot.mouseMove(component.getLocationOnScreen().x, component.getLocationOnScreen().y);
        bot.mousePress(InputEvent.BUTTON1_MASK);
        try{Thread.sleep(250);}catch(InterruptedException e){}
        bot.mouseRelease(InputEvent.BUTTON1_MASK);
    }
}
