package org.xper.rfplot.gui;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.Dependency;
import org.xper.console.ConsoleRenderer;
import org.xper.console.IConsolePlugin;
import org.xper.db.vo.RFInfoEntry;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.GLUtil;
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
import java.awt.event.*;
import java.util.*;
import java.util.List;
import java.util.function.BiConsumer;

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
    private JLabel rfDiameterLabel;
    private boolean isStimToggleOn = true;

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
        commandKeys.add(KeyStroke.getKeyStroke(KeyEvent.VK_F,0));
        commandKeys.add(KeyStroke.getKeyStroke(KeyEvent.VK_L,InputEvent.CTRL_DOWN_MASK));
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
        if(KeyStroke.getKeyStroke(KeyEvent.VK_L, InputEvent.CTRL_DOWN_MASK).equals(k)){
            System.out.println("Loading RFInfo");
            load();
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
        if(KeyStroke.getKeyStroke(KeyEvent.VK_F,0).equals(k)) {
            toggleStim();
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
        isStimToggleOn = true;
        RFPlotDrawable firstStimObj = namesForDrawables.get(stimType);
        stimSpec = RFPlotStimSpec.getStimSpecFromRFPlotDrawable(firstStimObj);
        client.changeRFPlotStim(stimSpec);
    }

    private void toggleStim() {
        isStimToggleOn = !isStimToggleOn;
        if (!isStimToggleOn) {
            RFPlotDrawable currentDrawable = new RFPlotBlankObject();
            client.changeRFPlotStim(RFPlotStimSpec.getStimSpecFromRFPlotDrawable(currentDrawable));
        } else {
            RFPlotDrawable firstStimObj = namesForDrawables.get(stimType);
            stimSpec = RFPlotStimSpec.getStimSpecFromRFPlotDrawable(firstStimObj);
            client.changeRFPlotStim(stimSpec);
            client.changeRFPlotXfm(xfmSpec);
        }
    }

    private void save(){
        AbstractRenderer renderer = consoleRenderer.getRenderer();
        final int depth = getEnteredDepth();
        plotter.getRfsForChannels().forEach(new BiConsumer<String, CircleRF>() {
            @Override
            public void accept(String channel, CircleRF circleRF) {
                if (circleRF.getCircleCenter() == null){
                    plotter.getRfsForChannels().remove(channel);
                    return;
                }

                Coordinates2D circleCenterDeg = mm2deg(circleRF.getCircleCenter());
                double radiusDeg = renderer.mm2deg(circleRF.getCircleRadius());
                List<Coordinates2D> circlePoints = circleRF.getCirclePoints();
                RFInfo rfInfo = new RFInfo(circleCenterDeg, radiusDeg, circlePoints);
                dbUtil.writeRFInfo(timeUtil.currentTimeMicros(), channel, rfInfo.toXml(), depth);
            }
        });

        namesForDrawables.forEach(new BiConsumer<String, RFPlotDrawable>() {
            @Override
            public void accept(String objectName, RFPlotDrawable rfPlotDrawable) {
                String data = rfPlotDrawable.getOutputData();
                writeRFObjectData(currentChannel, objectName, data, timeUtil.currentTimeMicros(), depth);
            }
        });
    }

    /**
     * Load the latest saved RF for every channel at the currently entered depth.
     * <p>
     * For each channel with RF data at this depth, the entry with the highest
     * tstamp (the latest) is restored: the channel is selected in the plotter
     * (which assigns it a legend color) and its control points are re-added so
     * the enclosing circle is recomputed. The legend is refreshed at the end.
     */
    private void load(){
        int depth = getEnteredDepth();
        List<RFInfoEntry> latestPerChannel;
        try {
            latestPerChannel = dbUtil.readLatestRFInfoPerChannel(depth);
        } catch (Exception e) {
            System.err.println("Failed to read RFs from database: " + e.getMessage());
            return;
        }
        if (latestPerChannel.isEmpty()) {
            System.out.println("No saved RFs found at depth " + depth + " µm.");
            return;
        }

        int loaded = 0;
        for (RFInfoEntry rfInfoEntry : latestPerChannel) {
            String channel = rfInfoEntry.getChannel();
            if (channel == null || channel.trim().isEmpty()) {
                System.err.println("Skipping RF with no channel (tstamp " + rfInfoEntry.getTstamp() + ").");
                continue;
            }
            try {
                RFInfo rfInfo = RFInfo.fromXml(rfInfoEntry.getInfo());

                // Select the channel so points are added to it and it gets a color.
                plotter.changeChannel(channel);
                CircleRF circleRF = new CircleRF(rfInfo.getCenter(), rfInfo.getRadius(), rfInfo.getControlPoints());
                for (Coordinates2D point : circleRF.getCirclePoints()) {
                    plotter.addCirclePoint(point);
                }
                loaded++;
                System.out.println("Loaded RF for channel " + channel + " (tstamp " + rfInfoEntry.getTstamp()
                        + ", depth " + rfInfoEntry.getDepth() + " µm).");
            } catch (Exception e) {
                // One malformed entry shouldn't abort loading the other channels.
                System.err.println("Skipping RF for channel " + channel + " (tstamp "
                        + rfInfoEntry.getTstamp() + "): " + e.getMessage());
            }
        }

        // Restore the channel selection the user had before loading.
        if (!currentChannel.equals("None")) {
            plotter.changeChannel(currentChannel);
        }
        updateLegend(plotter.getColorsForChannels());
        System.out.println("Loaded " + loaded + " RF(s) at depth " + depth + " µm.");
    }

    private void writeRFObjectData(String channel, String object, String data, long timestamp, int depth) {
        JdbcTemplate jt = new JdbcTemplate(dbUtil.getDataSource());
        jt.update(
                "INSERT INTO RFObjectData (tstamp, channel, object, data, depth) VALUES (?, ?, ?, ?, ?)",
                new Object[] {timestamp, channel, object, data, depth});

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

        // Left column: read-only RF information text.
        JPanel infoPanel = new JPanel(new GridBagLayout());
        rfCenterLabel(infoPanel);
        rfDiameterLabel(infoPanel);
        scrollerModeLabel(infoPanel);
        scrollerValueLabel(infoPanel);

        // Right column: channel controls (depth, selectors, remove button, legend).
        JPanel controlPanel = new JPanel(new GridBagLayout());
        depthField(controlPanel); // Optional depth (microns driven) for save/load
        channelSelectors(controlPanel); // Initialize and add the channel selectors
        removeButton(controlPanel); // Placed above the legend so it is always reachable
        legend(controlPanel);

        GridBagConstraints infoConstraints = new GridBagConstraints();
        infoConstraints.gridx = 0;
        infoConstraints.gridy = 0;
        infoConstraints.anchor = GridBagConstraints.NORTHWEST;
        infoConstraints.fill = GridBagConstraints.BOTH;
        infoConstraints.weightx = 0.5;
        infoConstraints.weighty = 1.0;
        infoConstraints.insets = new Insets(0, 0, 0, 10);
        jpanel.add(infoPanel, infoConstraints);

        GridBagConstraints controlConstraints = new GridBagConstraints();
        controlConstraints.gridx = 1;
        controlConstraints.gridy = 0;
        controlConstraints.anchor = GridBagConstraints.NORTHWEST;
        controlConstraints.fill = GridBagConstraints.BOTH;
        controlConstraints.weightx = 0.5;
        controlConstraints.weighty = 1.0;
        jpanel.add(controlPanel, controlConstraints);

        return jpanel;
    }

    private void removeButton(JPanel jpanel) {
        setupRemoveChannelButton(); // Initialize the button
        GridBagConstraints buttonConstraints = new GridBagConstraints();
        buttonConstraints.gridx = 0; // Adjust these constraints as needed
        buttonConstraints.gridy = 2; // Sits directly above the (scrollable) legend
        buttonConstraints.gridwidth = 2; // Span across two columns
        buttonConstraints.fill = GridBagConstraints.HORIZONTAL;
        jpanel.add(removeChannelButton, buttonConstraints);
    }

    private void legend(JPanel jpanel) {
        initLegendPanel(); // Initialize the legend panel
        // Wrap the legend in a bounded-height scroll pane. As channels are added
        // the legend overflows into columns and/or scrolls, so it can never push
        // the Remove Channel button off-screen.
        legendScrollPane = new JScrollPane(legendPanel);
        legendScrollPane.setBorder(BorderFactory.createTitledBorder("Channel Legend"));
        legendScrollPane.setPreferredSize(new Dimension(340, 160));
        legendScrollPane.setHorizontalScrollBarPolicy(JScrollPane.HORIZONTAL_SCROLLBAR_AS_NEEDED);
        legendScrollPane.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED);

        GridBagConstraints legendConstraints = new GridBagConstraints();
        legendConstraints.gridx = 0;
        legendConstraints.gridy = 3; // Below the Remove Channel button
        legendConstraints.gridwidth = 2; // Span across two columns if needed
        legendConstraints.fill = GridBagConstraints.BOTH;
        legendConstraints.weightx = 1.0;
        legendConstraints.weighty = 1.0;

        jpanel.add(legendScrollPane, legendConstraints);
    }

    private void depthField(JPanel jpanel) {
        GridBagConstraints depthLabelConstraints = new GridBagConstraints();
        depthLabelConstraints.gridx = 0;
        depthLabelConstraints.gridy = 0;
        depthLabelConstraints.gridwidth = 1;
        depthLabelConstraints.ipadx = 5;
        jpanel.add(new JLabel("Depth (µm driven)"), depthLabelConstraints);

        depthTextField = new JTextField(Integer.toString(currentDepth));
        depthTextField.setToolTipText("Microns driven. 0 = final recording location. " +
                "Ctrl+S saves at this depth; Ctrl+L loads the latest RF per channel at this depth.");
        GridBagConstraints depthFieldConstraints = new GridBagConstraints();
        depthFieldConstraints.gridx = 1;
        depthFieldConstraints.gridy = 0;
        depthFieldConstraints.gridwidth = 1;
        depthFieldConstraints.ipadx = 5;
        depthFieldConstraints.fill = GridBagConstraints.HORIZONTAL;
        jpanel.add(depthTextField, depthFieldConstraints);
    }

    /**
     * Parse the depth (microns driven) currently entered in the panel. Falls back
     * to 0 (final recording location) if the field is empty or not a valid integer.
     */
    private int getEnteredDepth() {
        if (depthTextField == null) {
            return currentDepth;
        }
        String text = depthTextField.getText().trim();
        if (text.isEmpty()) {
            return 0;
        }
        try {
            return Integer.parseInt(text);
        } catch (NumberFormatException e) {
            System.err.println("Invalid depth '" + text + "', using 0 (final recording location).");
            return 0;
        }
    }

    private void rfCenterLabel(JPanel jpanel) {
        GridBagConstraints centerLabelConstraints = new GridBagConstraints();
        centerLabelConstraints.gridx = 0;
        centerLabelConstraints.gridy = 0;
        centerLabelConstraints.gridwidth = 1;
        centerLabelConstraints.ipadx=5;
        centerLabelConstraints.anchor=GridBagConstraints.WEST;
        jpanel.add(new JLabel("Center"), centerLabelConstraints);

        rfCenterLabel = new JLabel(new Coordinates2D(0,0).toString());
        GridBagConstraints centerValueConstraints = new GridBagConstraints();
        centerValueConstraints.gridx = 1;
        centerValueConstraints.gridy = 0;
        centerValueConstraints.gridwidth = 1;
        centerValueConstraints.ipadx=5;
        centerValueConstraints.anchor=GridBagConstraints.WEST;
        jpanel.add(rfCenterLabel, centerValueConstraints);
        rfCenterLabel.setHorizontalAlignment(SwingConstants.LEFT);
        rfCenterLabel.setPreferredSize(new Dimension(320,20));
    }

    private void rfDiameterLabel(JPanel jpanel) {
        GridBagConstraints diameterLabelConstraints = new GridBagConstraints();
        diameterLabelConstraints.gridx = 0;
        diameterLabelConstraints.gridy = 1;
        diameterLabelConstraints.gridwidth = 1;
        diameterLabelConstraints.ipadx = 5;
        diameterLabelConstraints.anchor = GridBagConstraints.WEST;
        jpanel.add(new JLabel("Diameter"), diameterLabelConstraints);

        rfDiameterLabel = new JLabel("None");
        GridBagConstraints diameterValueConstraints = new GridBagConstraints();
        diameterValueConstraints.gridx = 1;
        diameterValueConstraints.gridy = 1;
        diameterValueConstraints.gridwidth = 1;
        diameterValueConstraints.ipadx = 5;
        diameterValueConstraints.anchor = GridBagConstraints.WEST;
        jpanel.add(rfDiameterLabel, diameterValueConstraints);
        rfDiameterLabel.setHorizontalAlignment(SwingConstants.LEFT);
        rfDiameterLabel.setPreferredSize(new Dimension(320, 20));
    }

    private void scrollerModeLabel(JPanel jpanel){
        GridBagConstraints scrollerModeConstraints = new GridBagConstraints();
        scrollerModeConstraints.gridx = 0;
        scrollerModeConstraints.gridy = 2;
        scrollerModeConstraints.gridwidth = 2;
        scrollerModeConstraints.anchor = GridBagConstraints.WEST;
        scrollerModeLabel = new JLabel("Mode");
        jpanel.add(scrollerModeLabel, scrollerModeConstraints);
    }

    private void scrollerValueLabel(JPanel jpanel){
        GridBagConstraints scrollerValueConstraints = new GridBagConstraints();
        scrollerValueConstraints.gridx = 0;
        scrollerValueConstraints.gridy = 3;
        scrollerValueConstraints.gridwidth = 2;
        scrollerValueConstraints.anchor = GridBagConstraints.WEST;
        scrollerValueLabel = new JLabel("Value");
        jpanel.add(scrollerValueLabel, scrollerValueConstraints);
    }
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
        gbc.gridy = 1;
        gbc.gridwidth = 1;
        gbc.fill = GridBagConstraints.HORIZONTAL;
        panel.add(letterComboBox, gbc);

        // Layout constraints for the number combobox
        gbc.gridx = 1;
        panel.add(numberComboBox, gbc);
    }

    private JPanel legendPanel;
    private JScrollPane legendScrollPane;
    private JTextField depthTextField;
    private int currentDepth = 0; // Microns driven; 0 = final recording location

    private List<JPanel> columns = new ArrayList<>();
    private int maxPerColumn = 5; // Maximum elements per column

    private void initLegendPanel() {
        legendPanel = new JPanel();
        legendPanel.setLayout(new BoxLayout(legendPanel, BoxLayout.X_AXIS));
        // Title border lives on the enclosing scroll pane (see legend()).

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
        if (legendScrollPane != null) {
            legendScrollPane.revalidate();
            legendScrollPane.repaint();
        }
    }




    @Override
    public void drawCanvas(Context context, String devId) {
        plotter.draw();
        drawCurrentStimPosition();
    }

    private void drawCurrentStimPosition() {
        AbstractRenderer renderer = consoleRenderer.getRenderer();
        RFPlotDrawable currentDrawable = getNamesForDrawables().get(stimType);
        List<Coordinates2D> outlinePoints = new ArrayList<>(currentDrawable.getOutlinePoints(renderer));

        //Shift the outline points to the current stim position
        List<Coordinates2D> shiftedOutlinePoints = new ArrayList<>();
        for (Coordinates2D point : outlinePoints) {
            shiftedOutlinePoints.add(new Coordinates2D(
                    point.getX() + currentStimPosition.getX(),
                    point.getY() + currentStimPosition.getY()
            ));
        }

        //Draw the outline with different colors based on toggle state
        float color = isStimToggleOn ? 1.0f : 0.5f;  // 1.0 = white, 0.5 = gray
        for (int i = 0; i < shiftedOutlinePoints.size(); i++) {
            Coordinates2D start = shiftedOutlinePoints.get(i);
            Coordinates2D end = shiftedOutlinePoints.get((i + 1) % shiftedOutlinePoints.size());
            GLUtil.drawLine(start.getX(), start.getY(), end.getX(), end.getY(), color, color, color);
        }
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
                    // Reset current selection (channel is chosen via the comboboxes).
                    currentChannel = "None";
                }
            }
        });
    }

    private void updateFromScroller(ScrollerParams newParams) {
        stimSpec = RFPlotStimSpec.getStimSpecFromRFPlotDrawable(newParams.getRfPlotDrawable());
        RFPlotDrawable currentDrawable = getNamesForDrawables().get(stimType);
        currentDrawable.setSpec(newParams.getRfPlotDrawable().getSpec());
        xfmSpec = newParams.getXfmSpec().toXml();
        if (isStimToggleOn) {
            client.changeRFPlotStim(stimSpec);
            client.changeRFPlotXfm(xfmSpec);
        }
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
            rfDiameterLabel.setText(Double.toString(renderer.mm2deg(plotter.getRFDiameter())));
        } catch (Exception ex) {
            rfCenterLabel.setText("None");
            rfDiameterLabel.setText("None");
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