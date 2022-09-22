package org.xper.rfplot.gui;

import org.xper.Dependency;
import org.xper.console.IConsolePlugin;
import org.xper.rfplot.RFPlotTaskDataSourceClient;
import org.xper.util.GuiUtil;

import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;

public class RFPlotGUIController extends JFrame {

    @Dependency
    RFPlotGUIView view;

    @Dependency
    RFPlotGuiModel model;

    public void initView(){
        view.getStimTextField().setText(model.getStim());
        view.getXfmTextField().setText(model.getXfm());
    }

    public void initController(){
        view.getSaveButton().addActionListener(new AbstractAction() {
            @Override
            public void actionPerformed(ActionEvent e) {
                save();
            }
        });
    }

    private void save(){
        System.out.println("Saved");
        model.setStim(view.getStimTextField().getText());
        model.setXfm(view.getXfmLabel().getText());
    }

    public RFPlotGUIView getView() {
        return view;
    }

    public void setView(RFPlotGUIView view) {
        this.view = view;
    }

    public RFPlotGuiModel getModel() {
        return model;
    }

    public void setModel(RFPlotGuiModel model) {
        this.model = model;
    }
}
