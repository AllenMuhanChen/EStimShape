package org.xper.rfplot.gui;

import org.xper.Dependency;

import javax.swing.*;
import java.awt.event.ActionEvent;

public class RFPlotGUIController extends JFrame {

    @Dependency
    RFPlotGUITestView view;

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
        model.setStim(view.getStimTextField().getText());
        model.setXfm(view.getXfmTextField().getText());
    }

    public RFPlotGUITestView getView() {
        return view;
    }

    public void setView(RFPlotGUITestView view) {
        this.view = view;
    }

    public RFPlotGuiModel getModel() {
        return model;
    }

    public void setModel(RFPlotGuiModel model) {
        this.model = model;
    }
}
