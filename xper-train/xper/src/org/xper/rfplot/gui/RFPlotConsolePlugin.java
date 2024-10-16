package org.xper.rfplot.gui;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.Dependency;
import org.xper.console.ConsoleRenderer;
import org.xper.console.IConsolePlugin;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.GLUtil;
import org.xper.drawing.RGBColor;
import org.xper.drawing.object.Circle;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.rfplot.*;
import org.xper.rfplot.drawing.RFPlotBlankObject;
import org.xper.rfplot.drawing.RFPlotDrawable;

import org.xper.rfplot.gui.scroller.ScrollerParams;
import org.xper.time.TimeUtil;
import org.xper.util.DbUtil;

import javax.swing.*;
import java.awt.*;
import java.awt.event.*;
import java.security.Key;
import java.util.*;
import java.util.List;
import java.util.function.BiConsumer;

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
    private boolean isMouseMoveStimuliModeOn = true;
    private Coordinates2D currentStimPosition;

    @Override
    /**
     * Must modify this to include all the command keys you want to use
     */
    public List<KeyStroke> getCommandKeys() {
        List<KeyStroke> commandKeys = new LinkedList<>();
        commandKeys.add(KeyStroke.getKeyStroke(KeyEvent.VK_A,0));
        commandKeys.add(KeyStroke.getKeyStroke(KeyEvent.VK_D,0));
        commandKeys.add(KeyStroke.getKeyStroke(KeyEvent.VK_W,0));
        commandKeys.add(KeyStroke.getKeyStroke(KeyEvent.VK_S,0));
        commandKeys.add(KeyStroke.getKeyStroke(KeyEvent.VK_Q,0));
        commandKeys.add(KeyStroke.getKeyStroke(KeyEvent.VK_S, InputEvent.CTRL_DOWN_MASK));
        commandKeys.add(KeyStroke.getKeyStroke(KeyEvent.VK_UP,0));
        commandKeys.add(KeyStroke.getKeyStroke(KeyEvent.VK_LEFT,0));
        commandKeys.add(KeyStroke.getKeyStroke(KeyEvent.VK_RIGHT,0));
        commandKeys.add(KeyStroke.getKeyStroke(KeyEvent.VK_DOWN,0));
        return commandKeys;
    }

    @Override
    public void handleKeyStroke(KeyStroke k) {
        System.out.println("KeyStroke: " + k.getKeyCode());
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
        if(KeyStroke.getKeyStroke(KeyEvent.VK_Q,0).equals(k)){
            isMouseMoveStimuliModeOn = !isMouseMoveStimuliModeOn;
            System.out.println("Move Stimuli Mode: " + isMouseMoveStimuliModeOn);
        }
        if(KeyStroke.getKeyStroke(KeyEvent.VK_S, InputEvent.CTRL_DOWN_MASK).equals(k)){
            System.out.println("Saving RFInfo");
            save();
        }
        if(KeyStroke.getKeyStroke(KeyEvent.VK_UP,0).equals(k)){
            updateStimPosition(new Coordinates2D(currentStimPosition.getX(), currentStimPosition.getY() + 1));
        }
        if(KeyStroke.getKeyStroke(KeyEvent.VK_DOWN,0).equals(k)){
            updateStimPosition(new Coordinates2D(currentStimPosition.getX(), currentStimPosition.getY() - 1));
        }
        if(KeyStroke.getKeyStroke(KeyEvent.VK_LEFT,0).equals(k)){
            updateStimPosition(new Coordinates2D(currentStimPosition.getX() - 1, currentStimPosition.getY()));
        }
        if(KeyStroke.getKeyStroke(KeyEvent.VK_RIGHT,0).equals(k)){
            updateStimPosition(new Coordinates2D(currentStimPosition.getX() + 1, currentStimPosition.getY()));
        }
    }

    private void updateStimPosition(Coordinates2D newStimPosition) {
        RFPlotXfmSpec nowXfmSpec = RFPlotXfmSpec.fromXml(xfmSpec);

        currentStimPosition = newStimPosition;
        nowXfmSpec.setTranslation(newStimPosition);

        xfmSpec = nowXfmSpec.toXml();
        client.changeRFPlotXfm(xfmSpec);
    }

    private void changeStimType(String stimType) {
        this.stimType = stimType;
        RFPlotDrawable firstStimObj = namesForDrawables.get(stimType);
        stimSpec = RFPlotStimSpec.getStimSpecFromRFPlotDrawable(firstStimObj);
        client.changeRFPlotStim(stimSpec);
    }

    private void save(){
        AbstractRenderer renderer = consoleRenderer.getRenderer();
        plotter.getRfsForChannels().forEach(new BiConsumer<String, CircleRF>() {
            @Override
            public void accept(String channel, CircleRF circleRF) {

                Coordinates2D circleCenterDeg = mm2deg(circleRF.getCircleCenter());
                double radiusDeg = renderer.mm2deg(circleRF.getCircleRadius());

                List<Coordinates2D> interpolatedOutlineDeg = plotter.getInterpolatedOutline(channel);
                for (Coordinates2D point : interpolatedOutlineDeg) {
                    point.setX(point.getX());
                    point.setY(point.getY());
                }

                RFInfo rfInfo = new RFInfo(interpolatedOutlineDeg, circleCenterDeg, radiusDeg);
                dbUtil.writeRFInfo(timeUtil.currentTimeMicros(), channel, rfInfo.toXml());
            }
        });

        namesForDrawables.forEach(new BiConsumer<String, RFPlotDrawable>() {
            @Override
            public void accept(String objectName, RFPlotDrawable rfPlotDrawable) {
                String data = rfPlotDrawable.getOutputData();
                writeRFObjectData(currentChannel, objectName, data, timeUtil.currentTimeMicros());
            }
        });
    }

    private void writeRFObjectData(String channel, String object, String data, long timestamp) {
        JdbcTemplate jt = new JdbcTemplate(dbUtil.getDataSource());
        jt.update(
                "INSERT INTO RFObjectData (tstamp, channel, object, data) VALUES (?, ?, ?, ?)",
                new Object[] {timestamp, channel, object, data});

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
        channelSelectors(jpanel); // Initialize and add the channel selectors
        legend(jpanel);
        removeButton(jpanel);
        return jpanel;
    }

    private void removeButton(JPanel jpanel) {
        setupRemoveChannelButton(); // Initialize the button
        GridBagConstraints buttonConstraints = new GridBagConstraints();
        buttonConstraints.gridx = 0; // Adjust these constraints as needed
        buttonConstraints.gridy = 6; // Place it below the last component
        buttonConstraints.gridwidth = 2; // Span across two columns
        buttonConstraints.fill = GridBagConstraints.HORIZONTAL;
        jpanel.add(removeChannelButton, buttonConstraints);
    }

    private void legend(JPanel jpanel) {
        initLegendPanel(); // Initialize the legend panel
        GridBagConstraints legendConstraints = new GridBagConstraints();
        legendConstraints.gridx = 0;
        legendConstraints.gridy = 5; // Adjust as necessary
        legendConstraints.gridwidth = 2; // Span across two columns if needed
        legendConstraints.fill = GridBagConstraints.HORIZONTAL;

        jpanel.add(legendPanel, legendConstraints);
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
    private JTextField channelTextField;
    private String currentChannel = "None"; // Default value or retrieve from a saved state
    private JComboBox<String> letterComboBox;
    private JComboBox<String> numberComboBox;

    private void channelSelectors(JPanel panel) {
        // Letters ComboBox
        String[] letters = {"A", "B", "C", "D", "SUPRA"};
        letterComboBox = new JComboBox<>(letters);

        // Numbers ComboBox
        String[] numbers = new String[32];
        for (int i = 0; i < numbers.length; i++) {
            numbers[i] = String.format("%03d", i); // Format as three digits
        }
        numberComboBox = new JComboBox<>(numbers);

        // Combine the selections and update currentChannel when either combobox changes
        ActionListener comboboxListener = new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                String selectedLetter = (String) letterComboBox.getSelectedItem();
                String selectedNumber = (String) numberComboBox.getSelectedItem();
                currentChannel = selectedLetter + "-" + selectedNumber;
                plotter.changeChannel(currentChannel);
                RFPlotConsolePlugin.this.updateLegend(plotter.getColorsForChannels());
            }
        };

        numberComboBox.addActionListener(comboboxListener);

        // Layout constraints for the letter combobox
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.gridx = 0;
        gbc.gridy = 4;
        gbc.gridwidth = 1;
        gbc.fill = GridBagConstraints.HORIZONTAL;
        panel.add(letterComboBox, gbc);

        // Layout constraints for the number combobox
        gbc.gridx = 1;
        panel.add(numberComboBox, gbc);
    }

    private JPanel legendPanel;

    private List<JPanel> columns = new ArrayList<>();
    private int maxPerColumn = 5; // Maximum elements per column

    private void initLegendPanel() {
        legendPanel = new JPanel();
        legendPanel.setLayout(new BoxLayout(legendPanel, BoxLayout.X_AXIS));
        legendPanel.setBorder(BorderFactory.createTitledBorder("Channel Legend"));

        addNewColumn(); // Initialize with one column
    }

    private void addNewColumn() {
        JPanel column = new JPanel();
        column.setLayout(new BoxLayout(column, BoxLayout.Y_AXIS));
        columns.add(column);
        legendPanel.add(column);
    }



    private void updateLegend(Map<String, RGBColor> colorsForChannels) {
        // Clear existing columns
        legendPanel.removeAll();
        columns.clear();
        addNewColumn(); // Start with a fresh column

        int itemCount = 0;

        for (Map.Entry<String, RGBColor> entry : colorsForChannels.entrySet()) {
            if (itemCount >= maxPerColumn) {
                addNewColumn(); // Add a new column if the current one is full
                itemCount = 0; // Reset item count for the new column
            }

            JPanel pairPanel = new JPanel();
            pairPanel.setLayout(new FlowLayout(FlowLayout.LEFT));

            JPanel colorIndicator = new JPanel();
            colorIndicator.setPreferredSize(new Dimension(10, 10));
            colorIndicator.setBackground(new Color(entry.getValue().getRed(), entry.getValue().getGreen(), entry.getValue().getBlue()));
            pairPanel.add(colorIndicator);

            JLabel channelLabel = new JLabel(entry.getKey());
            pairPanel.add(channelLabel);

            // Add the pair to the last column in the list
            columns.get(columns.size() - 1).add(pairPanel);

            itemCount++;
        }

        // Refresh layout
        legendPanel.revalidate();
        legendPanel.repaint();
    }




    @Override
    public void drawCanvas(Context context, String devId) {
        plotter.draw();
        GLUtil.drawCircle(new Circle(true, 5), currentStimPosition.getX(), currentStimPosition.getY(), 0, 255, 255, 255);
    }

    @Override
    public void handleMouseMove(int x, int y) {
        if (isMouseMoveStimuliModeOn) {
            updateStimPosition(mouseWorldPosition(x, y));
        }
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

    private JButton removeChannelButton;

    private void setupRemoveChannelButton() {
        removeChannelButton = new JButton("Remove Channel");
        removeChannelButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                if (!currentChannel.equals("None")) {
                    plotter.removeChannel(currentChannel); // Assuming such a method exists in plotter
                    updateLegend(plotter.getColorsForChannels()); // Refresh the legend to reflect the removal
                    // Optionally reset currentChannel if needed
                    currentChannel = "None";
                    channelTextField.setText(currentChannel);
                }
            }
        });
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
            List<Coordinates2D> outlinePoints = currentDrawable.getOutlinePoints(renderer);

            correctOutlinePoints(outlinePoints);

            plotter.addOutlinePoints(outlinePoints);
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

    private void correctOutlinePoints(List<Coordinates2D> profilePoints) {
        RFPlotXfmSpec rfPlotXfmSpec = RFPlotXfmSpec.fromXml(xfmSpec);
        Coordinates2D scale = rfPlotXfmSpec.getScale();
        float rotation = rfPlotXfmSpec.getRotation();
        Coordinates2D translation = rfPlotXfmSpec.getTranslation();

        // Correct profile points with scale and rotation
        for (Coordinates2D point : profilePoints) {
            double x = point.getX();
            double y = point.getY();
            point.setX(x * Math.cos(rotation) - y * Math.sin(rotation));
            point.setY(x * Math.sin(rotation) + y * Math.cos(rotation));
            point.setX(point.getX() * scale.getX());
            point.setY(point.getY() * scale.getY());
        }

        // Correct profile points with translation
        for (Coordinates2D point : profilePoints) {
            point.setX(point.getX() + translation.getX());
            point.setY(point.getY() + translation.getY());
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