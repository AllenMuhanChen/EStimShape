package org.xper.rfplot;

public interface RFPlotClient {
    void shutdownRFPlotTaskDataSourceServer();

    void changeRFPlotStim(String stim);

    void changeRFPlotXfm(String xfm);

    String getHost();

    int getPort();

    void setHost(String host);

    void setPort(int port);
}
