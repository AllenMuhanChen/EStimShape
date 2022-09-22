package org.xper.app.rfplot;

import org.xper.rfplot.gui.RFPlotGUIController;
import org.xper.rfplot.gui.RFPlotGUIView;
import org.xper.rfplot.gui.RFPlotGuiModel;

public class RFPlotGui {
    public static void main(String[] args) {
        RFPlotGuiModel model = new RFPlotGuiModel();
        RFPlotGUIView view = new RFPlotGUIView();
        RFPlotGUIController controller = new RFPlotGUIController();
        controller.setModel(model);
        controller.setView(view);
        controller.initController();
    }
}
