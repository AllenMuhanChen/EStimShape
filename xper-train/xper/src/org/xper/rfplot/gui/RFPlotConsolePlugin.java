package org.xper.rfplot.gui;

import org.xper.Dependency;
import org.xper.app.rfplot.CyclicIterator;
import org.xper.console.ConsoleRenderer;
import org.xper.console.IConsolePlugin;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.rfplot.*;
import org.xper.util.StringUtil;

import javax.swing.*;
import java.awt.event.KeyEvent;
import java.awt.event.MouseEvent;
import java.awt.event.MouseWheelEvent;
import java.util.*;

public class RFPlotConsolePlugin implements IConsolePlugin {
    @Dependency
    RFPlotClient client;

    @Dependency
    LinkedHashMap<String, RFPlotDrawable> rfObjectMap;

    @Dependency
    ConsoleRenderer consoleRenderer;

    private String xfmSpec;
    private String stimSpec;
    private CyclicIterator<String> types;


    @Override
    public void handleKeyStroke(KeyStroke k) {
        if (KeyStroke.getKeyStroke(KeyEvent.VK_D, 0).equals(k)) {
            String nextType = types.next();
            changeStimType(nextType);
        }
        if (KeyStroke.getKeyStroke(KeyEvent.VK_A, 0).equals(k)){
            String previousType = types.previous();
            changeStimType(previousType);
        }
    }

    private void changeStimType(String stimType) {
        RFPlotDrawable firstStimObj = rfObjectMap.get(stimType);
        RFPlotStimSpec stimSpec = new RFPlotStimSpec();
        stimSpec.setStimSpec(firstStimObj.getSpec());
        stimSpec.setStimClass(firstStimObj.getClass().getName());
        client.changeRFPlotStim(stimSpec.toXml());
        System.err.println(stimType);
    }

    private void init() {
        types = new CyclicIterator<String>(rfObjectMap.keySet());
        String firstType = types.first();
        try{changeStimType(firstType);} catch (Exception e){}
    }

    @Override
    public void stopPlugin() {
    }

    @Override
    public void startPlugin() {
        init();
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

        nowXfmSpec.setTranslation(mouseWorldPosition(x,y));

        xfmSpec = nowXfmSpec.toXml();
        client.changeRFPlotXfm(xfmSpec);
    }

    public Coordinates2D mouseWorldPosition(int x, int y) {
        AbstractRenderer renderer = consoleRenderer.getRenderer();
        Coordinates2D world = renderer.pixel2coord(new Coordinates2D(x, y));

        return world;
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
        return KeyStroke.getKeyStroke(KeyEvent.VK_R, 0);
    }

    @Override
    public List<KeyStroke> getCommandKeys() {
        List<KeyStroke> commandKeys = new LinkedList<>();
        commandKeys.add(KeyStroke.getKeyStroke(KeyEvent.VK_A,0));
        commandKeys.add(KeyStroke.getKeyStroke(KeyEvent.VK_D,0));
        return commandKeys;
    }

    @Override
    public String getPluginHelp() {
        return "null";
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

    public void setRfObjectMap(LinkedHashMap<String, RFPlotDrawable> rfObjectMap) {
        this.rfObjectMap = rfObjectMap;
    }

    public ConsoleRenderer getConsoleRenderer() {
        return consoleRenderer;
    }

    public void setConsoleRenderer(ConsoleRenderer consoleRenderer) {
        this.consoleRenderer = consoleRenderer;
    }
}
