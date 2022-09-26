package org.xper.rfplot.gui;

import org.xper.Dependency;
import org.xper.console.IConsolePlugin;
import org.xper.drawing.Context;
import org.xper.rfplot.RFPlotClient;
import org.xper.rfplot.RFPlotDrawable;
import org.xper.rfplot.RFPlotTaskDataSourceClient;

import javax.swing.*;
import java.awt.event.MouseEvent;
import java.awt.event.MouseWheelEvent;
import java.util.HashMap;
import java.util.List;

public class RFPlotConsolePlugin implements IConsolePlugin {
    @Dependency
    RFPlotClient client;

    @Dependency
    HashMap<String, RFPlotDrawable> rfObjectMap;

    private String xfmSpec;
    private String stimSpec;

    @Override
    public void handleKeyStroke(KeyStroke k) {

    }

    @Override
    public void stopPlugin() {

    }

    @Override
    public void startPlugin() {
        String firstStimType = String.valueOf(rfObjectMap.keySet().stream().findFirst());
        RFPlotDrawable firstStimObj = rfObjectMap.get(firstStimType);
        firstStimObj.getDefaultSpec();
    }

    @Override
    public void drawCanvas(Context context, String devId) {

    }

    @Override
    public void handleMouseMove(int x, int y) {
//        String xfm =
    }

    @Override
    public void handleMouseWheel(MouseWheelEvent e) {

    }

    @Override
    public String getPluginName() {
        return "RFPlot Mode";
    }

    @Override
    public KeyStroke getToken() {
        return null;
    }

    @Override
    public List<KeyStroke> getCommandKeys() {
        return null;
    }

    @Override
    public String getPluginHelp() {
        return null;
    }

    @Override
    public void handleMouseClicked(MouseEvent e) {

    }
}
