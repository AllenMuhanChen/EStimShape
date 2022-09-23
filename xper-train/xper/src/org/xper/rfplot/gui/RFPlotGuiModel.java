package org.xper.rfplot.gui;

import org.xper.Dependency;
import org.xper.rfplot.RFPlotClient;
import org.xper.rfplot.RFPlotTaskDataSourceClient;

public class RFPlotGuiModel {

    @Dependency
    RFPlotClient client;

    String stim;

    String xfm;

    public RFPlotClient getClient() {
        return client;
    }

    public void setClient(RFPlotClient client) {
        this.client = client;
    }

    public String getStim() {
        return stim;
    }

    public void setStim(String stim) {
        this.stim = stim;
        client.changeRFPlotStim(stim);
    }

    public String getXfm() {
        return xfm;
    }

    public void setXfm(String xfm) {
        this.xfm = xfm;
        client.changeRFPlotXfm(xfm);
    }
}
