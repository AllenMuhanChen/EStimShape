package org.xper.fixtrain.console;

import org.xper.Dependency;
import org.xper.console.IConsolePlugin;
import org.xper.drawing.Context;
import org.xper.fixtrain.FixTrainStimSpec;
import org.xper.fixtrain.drawing.FixTrainDrawable;
import org.xper.rfplot.gui.CyclicIterator;

import javax.swing.*;
import java.awt.event.KeyEvent;
import java.awt.event.MouseEvent;
import java.awt.event.MouseWheelEvent;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

public class FixTrainConsolePlugin implements IConsolePlugin {
    public static final int MAX_CALIBRATION_DEGREE = 30;
    @Dependency
    Map<String, FixTrainDrawable<?>> fixTrainObjectMap;

    @Dependency
    FixTrainClient client;

    @Dependency
    double calibrationDegree;

    private final static double SIZE_SCALE_FACTOR = 0.1;

    private String currentStimType;
    private FixTrainDrawable<?> currentStim;
    private CyclicIterator<String> stimTypeSpecs;


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
        if (KeyStroke.getKeyStroke(KeyEvent.VK_W, 0).equals(k)){
            nextCalibrationDegree();
            updateToCurrentStim();
        }
        if (KeyStroke.getKeyStroke(KeyEvent.VK_S, 0).equals(k)){
            previousCalibrationDegree();
            updateToCurrentStim();
        }
    }

    private void changeStimType(String nextStimType) {
        this.currentStimType = nextStimType;
        updateToCurrentStim();
        System.out.println("Stim type changed to " + currentStimType);
    }

    private void updateToCurrentStim(){
        currentStim = fixTrainObjectMap.get(currentStimType);
        String currentStimSpec = FixTrainStimSpec.getStimSpecFromFixTrainDrawable(currentStim, calibrationDegree);
        client.changeStim(currentStimSpec);
    }

    @Override
    public void stopPlugin() {

    }

    @Override
    public void startPlugin() {
        stimTypeSpecs = new CyclicIterator<String>(fixTrainObjectMap.keySet());
        currentStimType = stimTypeSpecs.first();
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
            double scaleFactor = 1.0;
            if (clicks > 0) {
                for (int i = 0; i < clicks; i++) {
                    scaleFactor = 1.0 + SIZE_SCALE_FACTOR;
                }
            } else{
                scaleFactor = 1.0 - SIZE_SCALE_FACTOR;
            }
            currentStim = fixTrainObjectMap.get(currentStimType);
            currentStim.scaleSize(scaleFactor);
            String currentStimSpec = FixTrainStimSpec.getStimSpecFromFixTrainDrawable(currentStim, calibrationDegree);
            client.changeStim(currentStimSpec);
            System.out.println("Size changed to " + currentStim.getSize().toString());
        }
    }


    private void nextCalibrationDegree() {
        double scaleFactor = 1.0 + SIZE_SCALE_FACTOR;
    	calibrationDegree = calibrationDegree * scaleFactor;
        if ( calibrationDegree > MAX_CALIBRATION_DEGREE) {
            calibrationDegree = MAX_CALIBRATION_DEGREE;
        }
        System.out.println("Calibration degree changed to " + calibrationDegree);
    }

    private void previousCalibrationDegree() {
        double scaleFactor = 1.0 - SIZE_SCALE_FACTOR;
        calibrationDegree = calibrationDegree * scaleFactor;
        System.out.println("Calibration degree changed to " + calibrationDegree);
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
        keys.add(KeyStroke.getKeyStroke(KeyEvent.VK_W, 0));
        keys.add(KeyStroke.getKeyStroke(KeyEvent.VK_S, 0));
        return keys;
    }

    @Override
    public String getPluginHelp() {
        return "FixTrain";
    }

    @Override
    public void handleMouseClicked(MouseEvent e) {

    }

    public Map<String, FixTrainDrawable<?>> getFixTrainObjectMap() {
        return fixTrainObjectMap;
    }

    public void setFixTrainObjectMap(Map<String, FixTrainDrawable<?>> fixTrainObjectMap) {
        this.fixTrainObjectMap = fixTrainObjectMap;
    }

    public FixTrainClient getClient() {
        return client;
    }

    public void setClient(FixTrainClient client) {
        this.client = client;
    }

    public double getCalibrationDegree() {
        return calibrationDegree;
    }

    public void setCalibrationDegree(double calibrationDegree) {
        this.calibrationDegree = calibrationDegree;
    }
}