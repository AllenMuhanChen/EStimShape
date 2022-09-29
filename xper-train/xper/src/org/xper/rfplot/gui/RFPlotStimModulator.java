package org.xper.rfplot.gui;

import org.xper.Dependency;
import org.xper.rfplot.RFPlotClient;
import org.xper.rfplot.drawing.RFPlotDrawable;

import java.util.LinkedHashMap;

public class RFPlotStimModulator {

    @Dependency
    protected RFPlotClient client;

    protected LinkedHashMap<String, RFPlotScroller> modeScrollerMap;
    public RFPlotStimModulator(LinkedHashMap<String, RFPlotScroller> modeScrollerMap) {
        this.modeScrollerMap = modeScrollerMap;

        modes = new CyclicIterator<String>(modeScrollerMap.keySet());
        currentScroller = modeScrollerMap.get(modes.first());
    }

    protected CyclicIterator<String> modes;
    protected RFPlotScroller currentScroller;

    public void nextMode(){
       currentScroller = modeScrollerMap.get(modes.next());
    }

    public void previousMode(){
        currentScroller = modeScrollerMap.get(modes.previous());
    }


    public void next(RFPlotDrawable drawable){
        currentScroller.next(drawable);
    }

    public void previous(RFPlotDrawable drawable) {
        currentScroller.previous(drawable);
    }

    public String getMode(){
        return modes.get(modes.getPosition());
    }

    public RFPlotClient getClient() {
        return client;
    }

    public void setClient(RFPlotClient client) {
        this.client = client;
    }

    public boolean hasScrollers(){
        return modes.hasNext();
    }
}
