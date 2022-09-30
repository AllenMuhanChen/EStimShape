package org.xper.rfplot.gui;

import org.xper.Dependency;
import org.xper.console.ConsoleRenderer;
import org.xper.console.IConsolePlugin;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.rfplot.*;
import org.xper.rfplot.drawing.RFPlotDrawable;
import org.xper.time.TimeUtil;
import org.xper.util.DbUtil;

import javax.swing.*;
import java.awt.event.InputEvent;
import java.awt.event.KeyEvent;
import java.awt.event.MouseEvent;
import java.awt.event.MouseWheelEvent;
import java.util.*;

/**
 * @author Allen Chen
 */
public class RFPlotConsolePlugin implements IConsolePlugin {
    @Dependency
    RFPlotClient client;

    @Dependency
    Map<String, RFPlotDrawable> refObjectMap;

    @Dependency
    Map<String, RFPlotStimModulator> refModulatorMap;

    @Dependency
    ConsoleRenderer consoleRenderer;

    @Dependency
    RFPlotDrawer plotter;

    @Dependency
    DbUtil dbUtil;

    @Dependency
    TimeUtil timeUtil;

    private String stimType;
    private String xfmSpec;
    private String stimSpec;
    private CyclicIterator<String> stimTypeSpecs;

    @Override
    public void handleKeyStroke(KeyStroke k) {
        if (KeyStroke.getKeyStroke(KeyEvent.VK_W, 0).equals(k)) {
            String nextType = stimTypeSpecs.next();
            changeStimType(nextType);
        }
        if (KeyStroke.getKeyStroke(KeyEvent.VK_S, 0).equals(k)){
            String previousType = stimTypeSpecs.previous();
            changeStimType(previousType);
        }
        if (KeyStroke.getKeyStroke(KeyEvent.VK_D, 0).equals(k)){
            refModulatorMap.get(stimType).nextMode();
        }
        if (KeyStroke.getKeyStroke(KeyEvent.VK_A, 0).equals(k)){
            refModulatorMap.get(stimType).previousMode();
        }
        if(KeyStroke.getKeyStroke(KeyEvent.VK_S, InputEvent.CTRL_DOWN_MASK).equals(k)){
            save();
        }
    }

    private void changeStimType(String stimType) {
        this.stimType = stimType;
        RFPlotDrawable firstStimObj = refObjectMap.get(stimType);
        stimSpec = RFPlotStimSpec.getStimSpecFromRFPlotDrawable(firstStimObj);
        client.changeRFPlotStim(stimSpec);
        System.err.println(stimType);
    }

    private void save(){
        RFInfo rfInfo = new RFInfo(mm2deg(plotter.getHull()), mm2deg(plotter.getRFCenter()));
        dbUtil.writeRFInfo(timeUtil.currentTimeMicros(), rfInfo.toXml());
    }

    private List<Coordinates2D> mm2deg(List<Coordinates2D> points) {
        List<Coordinates2D> hullInDegrees = new ArrayList<>();
        for (Coordinates2D pointInMM: points){
            Coordinates2D pointInDegrees = mm2deg(pointInMM);
            hullInDegrees.add(pointInDegrees);
        }
        return hullInDegrees;
    }

    private Coordinates2D mm2deg(Coordinates2D point){
        double x = consoleRenderer.getRenderer().mm2deg(point.getX());
        double y = consoleRenderer.getRenderer().mm2deg(point.getY());
        return new Coordinates2D(x,y);
    }

    @Override
    public void stopPlugin() {
    }

    @Override
    public void startPlugin() {
        init();
    }

    private void init() {
        stimTypeSpecs = new CyclicIterator<String>(refObjectMap.keySet());
    }

    @Override
    public void onSwitchToPlugin() {
        if(stimTypeSpecs.getPosition()==0)
            changeStimType(stimTypeSpecs.next());
    }

    @Override
    public void drawCanvas(Context context, String devId) {
        plotter.draw();
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
        Coordinates2D worldCoordinates = renderer.pixel2coord(new Coordinates2D(x, y));

        return worldCoordinates;
    }

    @Override
    public void handleMouseWheel(MouseWheelEvent e) {

        int clicks = e.getWheelRotation();
        System.err.println(clicks);
        RFPlotStimModulator modulator = refModulatorMap.get(stimType);

        if (modulator.hasScrollers()) {
            if (clicks > 0) {
                for (int i = 0; i < clicks; i++) {
                    ScrollerParams newParams = modulator.next(new ScrollerParams(
                            refObjectMap.get(stimType),
                            RFPlotXfmSpec.fromXml(xfmSpec)
                    ));
                    updateFromScroller(newParams);
                }
            } else {
                for (int i = 0; i > clicks; i--) {
                    ScrollerParams newParams = modulator.previous(new ScrollerParams(
                            refObjectMap.get(stimType),
                            RFPlotXfmSpec.fromXml(xfmSpec)
                    ));
                    updateFromScroller(newParams);
                }
            }
        }
    }

    private void updateFromScroller(ScrollerParams newParams) {
        stimSpec = RFPlotStimSpec.getStimSpecFromRFPlotDrawable(newParams.getRfPlotDrawable());
        xfmSpec = newParams.getXfmSpec().toXml();
        client.changeRFPlotStim(stimSpec);
        client.changeRFPlotXfm(xfmSpec);
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
        commandKeys.add(KeyStroke.getKeyStroke(KeyEvent.VK_W,0));
        commandKeys.add(KeyStroke.getKeyStroke(KeyEvent.VK_S,0));
        commandKeys.add(KeyStroke.getKeyStroke(KeyEvent.VK_S, InputEvent.CTRL_DOWN_MASK));
        return commandKeys;
    }

    @Override
    public String getPluginHelp() {
        return "null";
    }

    @Override
    public void handleMouseClicked(MouseEvent e) {

        //Left Click
        if (e.getButton() == MouseEvent.BUTTON1) {
            Coordinates2D worldCoords = mouseWorldPosition(e.getX(), e.getY());
            plotter.add(worldCoords);
            System.out.println(plotter.getRFCenter());
        }

        //Right Click
        if (e.getButton() == MouseEvent.BUTTON3) {
            Coordinates2D worldCoords = mouseWorldPosition(e.getX(), e.getY());
            plotter.removeClosestTo(worldCoords);
        }

        //Middle Mouse Click
        if (e.getButton() == MouseEvent.BUTTON2) {

        }
    }

    public RFPlotClient getClient() {
        return client;
    }

    public void setClient(RFPlotClient client) {
        this.client = client;
    }

    public Map<String, RFPlotDrawable> getRefObjectMap() {
        return refObjectMap;
    }

    public void setRefObjectMap(Map<String, RFPlotDrawable> refObjectMap) {
        this.refObjectMap = refObjectMap;
    }

    public ConsoleRenderer getConsoleRenderer() {
        return consoleRenderer;
    }

    public void setConsoleRenderer(ConsoleRenderer consoleRenderer) {
        this.consoleRenderer = consoleRenderer;
    }

    public Map<String, RFPlotStimModulator> getRefModulatorMap() {
        return refModulatorMap;
    }

    public void setRefModulatorMap(Map<String, RFPlotStimModulator> refModulatorMap) {
        this.refModulatorMap = refModulatorMap;
    }

    public RFPlotDrawer getPlotter() {
        return plotter;
    }

    public void setPlotter(RFPlotDrawer plotter) {
        this.plotter = plotter;
    }

    public DbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(DbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }

    public TimeUtil getTimeUtil() {
        return timeUtil;
    }

    public void setTimeUtil(TimeUtil timeUtil) {
        this.timeUtil = timeUtil;
    }
}
