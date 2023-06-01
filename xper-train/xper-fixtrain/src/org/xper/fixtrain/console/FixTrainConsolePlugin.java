package org.xper.fixtrain.console;

import org.xper.Dependency;
import org.xper.console.IConsolePlugin;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.fixtrain.FixTrainStimSpec;
import org.xper.fixtrain.FixTrainXfmSpec;
import org.xper.fixtrain.drawing.FixTrainDrawable;
import org.xper.rfplot.drawing.RFPlotDrawable;
import org.xper.rfplot.gui.CyclicIterator;

import javax.swing.*;
import java.awt.event.KeyEvent;
import java.awt.event.MouseEvent;
import java.awt.event.MouseWheelEvent;
import java.util.LinkedHashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

public class FixTrainConsolePlugin implements IConsolePlugin {
    @Dependency
    Map<String, FixTrainDrawable> fixTrainObjectMap;

    @Dependency
    FixTrainClient client;

    private final static double SCALE_FACTOR = 0.25;

    private String currentStimType;
    private String currentStimSpec;
    private String currentXfmSpec;
    private CyclicIterator<String> stimTypeSpecs;
    private double currentScaleFactor;

    @Override
    public void handleKeyStroke(KeyStroke k) {
        if (KeyStroke.getKeyStroke(KeyEvent.VK_A, 0).equals(k)){
            String nextStimType = stimTypeSpecs.next();
            changeStimType(nextStimType);
        }
        if (KeyStroke.getKeyStroke(KeyEvent.VK_D, 0).equals(k)){
            String prevStimType = stimTypeSpecs.previous();
            changeStimType(prevStimType);
        }
    }

    private void changeStimType(String nextStimType) {
        this.currentStimType = nextStimType;
        updateToCurrentStimType();
    }

    private void updateToCurrentStimType(){
        FixTrainDrawable drawable = fixTrainObjectMap.get(currentStimType);
        currentStimSpec = FixTrainStimSpec.getStimSpecFromFixTrainDrawable(drawable);
        client.changeStim(currentStimSpec);
        System.out.println("Stim type changed to " + currentStimType);
    }

    @Override
    public void stopPlugin() {

    }

    @Override
    public void startPlugin() {
        stimTypeSpecs = new CyclicIterator<String>(fixTrainObjectMap.keySet());
        currentStimType = stimTypeSpecs.first();
        currentXfmSpec = FixTrainXfmSpec.defaultXfmSpec().toXml();
    }

    @Override
    public void onSwitchToPluginAction() {

    }

    @Override
    public JPanel pluginPanel() {
        return null;
    }

    @Override
    public void drawCanvas(Context context, String devId) {

    }

    @Override
    public void handleMouseMove(int x, int y) {

    }

    @Override
    public void handleMouseWheel(MouseWheelEvent e) {
        int clicks = e.getWheelRotation();

        updateSize(clicks);
    }

    private void updateSize(int clicks) {
        if (clicks != 0) {
            if (clicks > 0) {
                for (int i = 0; i < clicks; i++) {
                    currentScaleFactor = nextSize(currentScaleFactor);
                }
            } else{
                currentScaleFactor = previousSize(currentScaleFactor);
            }
            FixTrainXfmSpec newXfm = FixTrainXfmSpec.fromXml(currentXfmSpec);
            newXfm.setScale(new Coordinates2D(currentScaleFactor, currentScaleFactor));
            currentXfmSpec = newXfm.toXml();
            client.changeXfm(currentXfmSpec);
            System.out.println("Scale changed to " + currentScaleFactor);

        }
    }

    private double nextSize(double currentScaleFactor) {
        return currentScaleFactor + (SCALE_FACTOR);
    }

    private double previousSize(double currentScaleFactor) {
        return currentScaleFactor - (1.0-SCALE_FACTOR);
    }

    @Override
    public String getPluginName() {
        return "fixation training";

    }

    @Override
    public KeyStroke getToken() {
        return KeyStroke.getKeyStroke(KeyEvent.VK_F, 0);
    }

    @Override
    public List<KeyStroke> getCommandKeys() {
        List<KeyStroke> keys = new LinkedList<KeyStroke>();
        keys.add(KeyStroke.getKeyStroke(KeyEvent.VK_A, 0));
        keys.add(KeyStroke.getKeyStroke(KeyEvent.VK_D, 0));
        return keys;
    }

    @Override
    public String getPluginHelp() {
        return "FixTrain";
    }

    @Override
    public void handleMouseClicked(MouseEvent e) {

    }

    public Map<String, FixTrainDrawable> getFixTrainObjectMap() {
        return fixTrainObjectMap;
    }

    public void setFixTrainObjectMap(Map<String, FixTrainDrawable> fixTrainObjectMap) {
        this.fixTrainObjectMap = fixTrainObjectMap;
    }

    public FixTrainClient getClient() {
        return client;
    }

    public void setClient(FixTrainClient client) {
        this.client = client;
    }
}