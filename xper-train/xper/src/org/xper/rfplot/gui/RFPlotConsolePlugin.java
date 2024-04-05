package org.xper.rfplot.gui;

import org.xper.Dependency;
import org.xper.console.ConsoleRenderer;
import org.xper.console.IConsolePlugin;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.rfplot.*;
import org.xper.rfplot.drawing.RFPlotBlankObject;
import org.xper.rfplot.drawing.RFPlotDrawable;
import org.xper.rfplot.gui.scroller.ScrollerParams;
import org.xper.time.TimeUtil;
import org.xper.util.DbUtil;

import javax.swing.*;
import java.awt.*;
import java.awt.event.InputEvent;
import java.awt.event.KeyEvent;
import java.awt.event.MouseEvent;
import java.awt.event.MouseWheelEvent;
import java.util.*;
import java.util.List;

import static java.awt.GridBagConstraints.PAGE_END;
import static java.awt.GridBagConstraints.PAGE_START;

/**
 * @author Allen Chen
 */
public class RFPlotConsolePlugin implements IConsolePlugin {
    @Dependency
    RFPlotClient client;

    @Dependency
    Map<String, RFPlotDrawable> namesForDrawables;

    @Dependency
    Map<String, RFPlotStimModulator> modulatorsForDrawables;

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
            RFPlotStimModulator modulator = modulatorsForDrawables.get(stimType);
            modulator.nextMode();
            scrollerModeLabel.setText(modulator.getMode());
        }
        if (KeyStroke.getKeyStroke(KeyEvent.VK_A, 0).equals(k)){
            RFPlotStimModulator modulator = modulatorsForDrawables.get(stimType);
            modulator.previousMode();
            scrollerModeLabel.setText(modulator.getMode());
        }
        if(KeyStroke.getKeyStroke(KeyEvent.VK_S, InputEvent.CTRL_DOWN_MASK).equals(k)){
            System.out.println("Saving RFInfo");
            save();
        }
    }

    private void changeStimType(String stimType) {
        this.stimType = stimType;
        RFPlotDrawable firstStimObj = namesForDrawables.get(stimType);
        stimSpec = RFPlotStimSpec.getStimSpecFromRFPlotDrawable(firstStimObj);
        client.changeRFPlotStim(stimSpec);
    }

    private void save(){
        RGBColor currentColor = RFPlotXfmSpec.fromXml(xfmSpec).getColor();
        V4RFInfo rfInfo = new V4RFInfo(mm2deg(plotter.getOutline()), mm2deg(plotter.getRFCenter()), currentColor);
        dbUtil.writeRFInfo(timeUtil.currentTimeMicros(), rfInfo.toXml());
    }

    private List<Coordinates2D> mm2deg(List<Coordinates2D> points) {
        List<Coordinates2D> pointsInDegrees = new ArrayList<>();
        for (Coordinates2D pointInMM: points){
            Coordinates2D pointInDegrees = mm2deg(pointInMM);
            pointsInDegrees.add(pointInDegrees);
        }
        return pointsInDegrees;
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
        stimTypeSpecs = new CyclicIterator<String>(namesForDrawables.keySet());
        stimType = stimTypeSpecs.first();
    }

    @Override
    public void onSwitchToPluginAction() {
        if(namesForDrawables.get(stimType) instanceof RFPlotBlankObject)
            changeStimType(stimTypeSpecs.next());
    }

    private JLabel rfCenterLabel;
    private JLabel scrollerModeLabel;
    private JLabel scrollerValueLabel;
    /**
     * https://docs.oracle.com/javase/tutorial/uiswing/layout/gridbag.html#:~:text=A%20GridBagLayout%20places%20components%20in,necessarily%20have%20the%20same%20width.
     * @return
     */
    @Override
    public JPanel pluginPanel() {
        JPanel jpanel = new JPanel();
        jpanel.setLayout(new GridBagLayout());
        jpanel.setBorder(BorderFactory.createTitledBorder("RFPlot"));

        rfCenterLabel(jpanel);
        scrollerModeLabel(jpanel);
        scrollerValueLabel(jpanel);
        return jpanel;
    }

    private void rfCenterLabel(JPanel jpanel) {
        GridBagConstraints centerLabelConstraints = new GridBagConstraints();
        centerLabelConstraints.gridwidth = 1;
        centerLabelConstraints.ipadx=5;
        centerLabelConstraints.anchor=PAGE_START;
        jpanel.add(new JLabel("Center"), centerLabelConstraints);

        rfCenterLabel = new JLabel(new Coordinates2D(0,0).toString());
        GridBagConstraints centerValueConstraints = new GridBagConstraints();
        centerValueConstraints.gridwidth = 1;
        centerValueConstraints.ipadx=5;
        centerValueConstraints.anchor=PAGE_END;
        jpanel.add(rfCenterLabel, centerValueConstraints);
        rfCenterLabel.setHorizontalAlignment(SwingConstants.LEFT);
        rfCenterLabel.setPreferredSize(new Dimension(320,20));
    }

    private void scrollerModeLabel(JPanel jpanel){
        GridBagConstraints scrollerModeConstraints = new GridBagConstraints();
        scrollerModeConstraints.gridy = 2;
        scrollerModeLabel = new JLabel("Mode");
        jpanel.add(scrollerModeLabel, scrollerModeConstraints);
    }

    private void scrollerValueLabel(JPanel jpanel){
        GridBagConstraints scrollerValueConstraints = new GridBagConstraints();
        scrollerValueConstraints.gridy = 3;
        scrollerValueLabel = new JLabel("Value");
        jpanel.add(scrollerValueLabel, scrollerValueConstraints);
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
        RFPlotStimModulator modulator = modulatorsForDrawables.get(stimType);

        if (modulator.hasScrollers()) {
            if (clicks > 0) {
                for (int i = 0; i < clicks; i++) {
                    ScrollerParams newParams = modulator.previous(new ScrollerParams(
                            namesForDrawables.get(stimType),
                            RFPlotXfmSpec.fromXml(xfmSpec)
                    ));
                    updateFromScroller(newParams);
                }
            } else {
                for (int i = 0; i > clicks; i--) {
                    ScrollerParams newParams = modulator.next(new ScrollerParams(
                            namesForDrawables.get(stimType),
                            RFPlotXfmSpec.fromXml(xfmSpec)
                    ));
                    updateFromScroller(newParams);
                }
            }

        }


    }

    private void updateFromScroller(ScrollerParams newParams) {
        stimSpec = RFPlotStimSpec.getStimSpecFromRFPlotDrawable(newParams.getRfPlotDrawable());
        RFPlotDrawable currentDrawable = getNamesForDrawables().get(stimType);
        currentDrawable.setSpec(newParams.getRfPlotDrawable().getSpec());
        xfmSpec = newParams.getXfmSpec().toXml();
        client.changeRFPlotStim(stimSpec);
        client.changeRFPlotXfm(xfmSpec);
        scrollerValueLabel.setText(newParams.getNewValue());
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
        AbstractRenderer renderer = consoleRenderer.getRenderer();
        Coordinates2D worldCoords = mouseWorldPosition(e.getX(), e.getY());
        RFPlotDrawable currentDrawable = getNamesForDrawables().get(stimType);

        Coordinates2D mouseCoordinatesInDegrees = new Coordinates2D(
                renderer.mm2deg(worldCoords.getX()),
                renderer.mm2deg(worldCoords.getY())
        );


        Coordinates2D mouseCoordinatesMm = new Coordinates2D(
                renderer.deg2mm(mouseCoordinatesInDegrees.getX()),
                renderer.deg2mm(mouseCoordinatesInDegrees.getY())
        );

        //Left Click
        if (e.getButton() == MouseEvent.BUTTON1) {
            plotter.addCirclePoint(mouseCoordinatesMm);
        }

        //Right Click
        if (e.getButton() == MouseEvent.BUTTON3) {
            plotter.removeClosestCirclePointTo(worldCoords);
        }

        //Middle Mouse Click
        if (e.getButton() == MouseEvent.BUTTON2 && !e.isShiftDown()) {
            List<Coordinates2D> profilePoints = currentDrawable.getOutlinePoints(renderer);

            RFPlotXfmSpec rfPlotXfmSpec = RFPlotXfmSpec.fromXml(xfmSpec);
            Coordinates2D scale = rfPlotXfmSpec.getScale();
            float rotation = rfPlotXfmSpec.getRotation();



            // Correct profile points with scale and rotation
            for (Coordinates2D point : profilePoints) {
                double x = point.getX();
                double y = point.getY();
                point.setX(x * Math.cos(rotation) - y * Math.sin(rotation));
                point.setY(x * Math.sin(rotation) + y * Math.cos(rotation));
                point.setX(point.getX() * scale.getX());
                point.setY(point.getY() * scale.getY());
            }

            // Correct profile points with mouse location
            for (Coordinates2D point : profilePoints) {
                point.setX(point.getX() + mouseCoordinatesMm.getX());
                point.setY(point.getY() + mouseCoordinatesMm.getY());
            }


            plotter.addOutlinePoints(profilePoints);
        }

        //Shift Middle Mouse Click
        if (e.getButton() == MouseEvent.BUTTON2 && e.isShiftDown()) {
            plotter.removeClosestOutlineTo(worldCoords);
        }

        try {
            rfCenterLabel.setText(mm2deg(plotter.getRFCenter()).toString());
        } catch (Exception ex) {
            rfCenterLabel.setText("None");
        }
    }

    public RFPlotClient getClient() {
        return client;
    }

    public void setClient(RFPlotClient client) {
        this.client = client;
    }

    public Map<String, RFPlotDrawable> getNamesForDrawables() {
        return namesForDrawables;
    }

    public void setNamesForDrawables(Map<String, RFPlotDrawable> namesForDrawables) {
        this.namesForDrawables = namesForDrawables;
    }

    public ConsoleRenderer getConsoleRenderer() {
        return consoleRenderer;
    }

    public void setConsoleRenderer(ConsoleRenderer consoleRenderer) {
        this.consoleRenderer = consoleRenderer;
    }

    public Map<String, RFPlotStimModulator> getModulatorsForDrawables() {
        return modulatorsForDrawables;
    }

    public void setModulatorsForDrawables(Map<String, RFPlotStimModulator> modulatorsForDrawables) {
        this.modulatorsForDrawables = modulatorsForDrawables;
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