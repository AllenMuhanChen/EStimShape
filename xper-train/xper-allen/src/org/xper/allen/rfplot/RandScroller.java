package org.xper.allen.rfplot;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.rfplot.RFPlotMatchStick.RFPlotMatchStickSpec;
import org.xper.rfplot.gui.scroller.RFPlotScroller;
import org.xper.rfplot.gui.scroller.ScrollerParams;

import java.util.LinkedList;
import java.util.List;

public class RandScroller<T extends RFPlotMatchStickSpec> extends RFPlotScroller<T> {

    List<RFPlotMatchStickSpec> savedSpecs = new LinkedList<>();
    int currentSpecIndex = 0;
    public RandScroller(Class<T> type) {
        this.type = type;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RFPlotMatchStickSpec currentSpec = getCurrentSpec(scrollerParams);
        RFPlotMatchStickSpec newSpec = new RFPlotMatchStickSpec(currentSpec);
        // Save the first spec
        if (savedSpecs.isEmpty()){
            System.out.println("saved first spec");
            savedSpecs.add(new RFPlotMatchStickSpec(newSpec));
        }


        currentSpecIndex++;
        AllenMatchStick newMStick = new AllenMatchStick();
        newMStick.setProperties(newSpec.getSizeDiameterDegrees(), newSpec.getTexture());
        newMStick.setStimColor(newSpec.getColor());

        AllenMStickSpec newMStickSpec = new AllenMStickSpec();
        if ((currentSpecIndex+1) > savedSpecs.size()){
            newMStick.genMatchStickRand();
            savedSpecs.add(newSpec);
            newSpec.setSpec(newMStick);
        } else{
            RFPlotMatchStickSpec savedSpec = savedSpecs.get(currentSpecIndex);
            newMStickSpec = savedSpec.getMStickSpec();
            newSpec.setSpec(newMStickSpec);
        }

        scrollerParams.getRfPlotDrawable().setSpec(newSpec.toXml());
        scrollerParams.setNewValue("Rand Matchstick: " + (currentSpecIndex + 1));
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        currentSpecIndex--;
        if (currentSpecIndex < 0){
            currentSpecIndex = 0;
        }
        RFPlotMatchStickSpec spec = savedSpecs.get(currentSpecIndex);
        spec.setSpec(spec.getMStickSpec());

        scrollerParams.getRfPlotDrawable().setSpec(spec.toXml());
        scrollerParams.setNewValue("Rand Matchstick: " + (currentSpecIndex + 1));
        return scrollerParams;
    }
}