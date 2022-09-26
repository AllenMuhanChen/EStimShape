package org.xper.rfplot.gui;

import org.xper.Dependency;
import org.xper.console.IConsolePlugin;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.rfplot.RFPlotClient;
import org.xper.rfplot.RFPlotDrawable;
import org.xper.rfplot.RFPlotTaskDataSourceClient;
import org.xper.rfplot.RFPlotXfmSpec;

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
        setDefaultStimSpec();
        setDefaultXfmSpec();
    }

    private void setDefaultStimSpec() {
        String firstStimType = String.valueOf(rfObjectMap.keySet().stream().findFirst().orElse(null));
        RFPlotDrawable firstStimObj = rfObjectMap.get(firstStimType);
        client.changeRFPlotStim(firstStimObj.getSpec());
    }

    private void setDefaultXfmSpec(){
        RFPlotXfmSpec xfmSpec = RFPlotXfmSpec.fromXml(null);
        client.changeRFPlotXfm(xfmSpec.toXml());
    }

    @Override
    public void drawCanvas(Context context, String devId) {

    }

    @Override
    public void handleMouseMove(int x, int y) {
        RFPlotXfmSpec nowXfmSpec = RFPlotXfmSpec.fromXml(xfmSpec);
        nowXfmSpec.setTranslation(new Coordinates2D(x,y));
        xfmSpec = nowXfmSpec.toXml();
        client.changeRFPlotXfm(xfmSpec);
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

    public RFPlotClient getClient() {
        return client;
    }

    public void setClient(RFPlotClient client) {
        this.client = client;
    }

    public HashMap<String, RFPlotDrawable> getRfObjectMap() {
        return rfObjectMap;
    }

    public void setRfObjectMap(HashMap<String, RFPlotDrawable> rfObjectMap) {
        this.rfObjectMap = rfObjectMap;
    }
}
