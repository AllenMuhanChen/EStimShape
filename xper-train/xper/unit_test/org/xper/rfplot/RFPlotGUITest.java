package org.xper.rfplot;

import org.junit.BeforeClass;
import org.junit.Test;
import org.xper.rfplot.gui.RFPlotGUIController;
import org.xper.rfplot.gui.RFPlotGUIView;
import org.xper.rfplot.gui.RFPlotGuiModel;

import javax.swing.*;
import java.awt.*;
import java.awt.event.InputEvent;

public class RFPlotGUITest {

    private RFPlotGUIView view;

    @BeforeClass
    public void setUp(){
        RFPlotGuiModel model = new RFPlotGuiModel();
        view = new RFPlotGUIView();
        RFPlotGUIController controller = new RFPlotGUIController();
        controller.setModel(model);
        controller.setView(view);
        controller.initController();
    }

    @Test
    public void save_button() throws AWTException {
        pressButton(view.getSaveButton());
    }

    private void pressButton(JButton button) throws AWTException {
        Robot bot = new Robot();
        bot.mouseMove(button.getLocationOnScreen().x, button.getLocationOnScreen().y);
        bot.mousePress(InputEvent.BUTTON1_MASK);
        try{Thread.sleep(250);}catch(InterruptedException e){}
        bot.mouseRelease(InputEvent.BUTTON1_MASK);
    }
}
