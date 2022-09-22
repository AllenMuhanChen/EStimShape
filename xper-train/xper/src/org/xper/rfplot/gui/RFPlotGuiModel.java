package org.xper.rfplot.gui;

import org.xper.Dependency;
import org.xper.rfplot.RFPlotTaskDataSourceClient;

public class RFPlotGuiModel {

    @Dependency
    RFPlotTaskDataSourceClient client;

    String stim;

    String xfm;

    public RFPlotTaskDataSourceClient getClient() {
        return client;
    }

    public void setClient(RFPlotTaskDataSourceClient client) {
        this.client = client;
    }

    public String getStim() {
        return stim;
    }

    public void setStim(String stim) {
        this.stim = stim;
    }

    public String getXfm() {
        return xfm;
    }

    public void setXfm(String xfm) {
        this.xfm = xfm;
    }
}
