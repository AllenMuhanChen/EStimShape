package org.xper.rfplot;

public class MockRFPlotTaskDataSourceClient implements RFPlotClient{
    private String mockStim;
    private String mockXfm;

    @Override
    public void shutdownRFPlotTaskDataSourceServer() {

    }

    public void changeRFPlotStim(String stim){
        this.mockStim = stim;
        System.out.println("Mock Send Stim to Client: " + mockStim);
    }

    @Override
    public void changeRFPlotXfm(String xfm) {
        this.mockXfm = xfm;
        System.out.println("Mock Send XFM to Client: " + mockXfm);
    }

    @Override
    public String getHost() {
        return null;
    }

    @Override
    public int getPort() {
        return 0;
    }

    @Override
    public void setHost(String host) {

    }

    @Override
    public void setPort(int port) {

    }

    public String getMockStim() {
        return mockStim;
    }

    public void setMockStim(String mockStim) {
        this.mockStim = mockStim;
    }

    public String getMockXfm() {
        return mockXfm;
    }

    public void setMockXfm(String mockXfm) {
        this.mockXfm = mockXfm;
    }
}
