package org.xper.rfplot.gui;

import org.xper.util.GuiUtil;

import javax.swing.*;
import java.awt.*;
import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;

public class RFPlotGUIView {

    private JFrame frame;
    private JLabel stimLabel;
    private JLabel xfmLabel;
    private JTextField stimTextField;
    private JTextField xfmTextField;
    private JButton saveButton;

    public RFPlotGUIView(){
        frame = new JFrame("RFPlot");

        //CONFIGURE FRAME
        frame.getContentPane().setLayout(new BoxLayout(frame.getContentPane(),BoxLayout.PAGE_AXIS));
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setResizable(true);
        GuiUtil.makeDisposeOnEscapeKey(frame);

        //CREATE UI ELEMENTS
        stimLabel = new JLabel("Stim: ");
        xfmLabel = new JLabel("xfm: ");
        stimTextField = new JTextField();
        xfmTextField = new JTextField();
        saveButton = new JButton("Save");

        //ADD UI ELEMENTS TO FRAME
        frame.getContentPane().add(stimLabel);
        frame.getContentPane().add(xfmLabel);
        frame.getContentPane().add(stimTextField);
        frame.getContentPane().add(xfmTextField);
        frame.getContentPane().add(saveButton);

        frame.setVisible(true);
    }

    public JFrame getFrame() {
        return frame;
    }

    public void setFrame(JFrame frame) {
        this.frame = frame;
    }

    public JLabel getStimLabel() {
        return stimLabel;
    }

    public void setStimLabel(JLabel stimLabel) {
        this.stimLabel = stimLabel;
    }

    public JLabel getXfmLabel() {
        return xfmLabel;
    }

    public void setXfmLabel(JLabel xfmLabel) {
        this.xfmLabel = xfmLabel;
    }

    public JTextField getStimTextField() {
        return stimTextField;
    }

    public void setStimTextField(JTextField stimTextField) {
        this.stimTextField = stimTextField;
    }

    public JTextField getXfmTextField() {
        return xfmTextField;
    }

    public void setXfmTextField(JTextField xfmTextField) {
        this.xfmTextField = xfmTextField;
    }

    public JButton getSaveButton() {
        return saveButton;
    }

    public void setSaveButton(JButton saveButton) {
        this.saveButton = saveButton;
    }
}
