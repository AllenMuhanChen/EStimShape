package org.xper.allen.rfplot;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.rfplot.RFPlotMatchStick.RFPlotMatchStickSpec;
import org.xper.rfplot.gui.scroller.RFPlotScroller;
import org.xper.rfplot.gui.scroller.ScrollerParams;

import java.util.LinkedList;
import java.util.List;

public class RandMStickScroller<T extends RFPlotMatchStickSpec> extends RFPlotScroller<T> {

    List<RFPlotMatchStickSpec> savedSpecs = new LinkedList<>();
    int currentSpecIndex = 0;
    public RandMStickScroller(Class<T> type) {
        this.type = type;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {

        // Get the current spec and create a new spec
        RFPlotMatchStickSpec currentSpec = getCurrentSpec(scrollerParams);
        RFPlotMatchStickSpec newSpec = new RFPlotMatchStickSpec(currentSpec);

        // Save the first spec
        if (savedSpecs.isEmpty()){
            savedSpecs.add(new RFPlotMatchStickSpec(newSpec));
        }


        currentSpecIndex++;

        // Create a new matchstick with same size, color, texture, etc... as the current matchstick
        AllenMatchStick newMStick = new AllenMatchStick();
        newMStick.setProperties(newSpec.getSizeDiameterDegrees(), newSpec.getTexture(), 1.0);
        newMStick.setStimColor(newSpec.getColor());

        AllenMStickSpec newMStickSpec = new AllenMStickSpec();
        if ((currentSpecIndex+1) > savedSpecs.size()){ //save new matchstick
            newMStick.genMatchStickRand();
            savedSpecs.add(newSpec);
            newSpec.setSpec(newMStick);
        } else{ //load saved matchstick
            RFPlotMatchStickSpec savedSpec = savedSpecs.get(currentSpecIndex);
            newMStickSpec = savedSpec.getMStickSpec();
            newSpec.setSpec(newMStickSpec);
        }

        // Set the new spec and update the drawable
        scrollerParams.getRfPlotDrawable().setSpec(newSpec.toXml());
        scrollerParams.setNewValue("Rand Matchstick: " + (currentSpecIndex + 1));
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        //update the currentSpecIndex and don't allow go below zero
        currentSpecIndex--;
        if (currentSpecIndex < 0){
            currentSpecIndex = 0;
        }

        // Make a new spec that has saved mStick info and current size, color, texture, etc...
        RFPlotMatchStickSpec currentSpec = getCurrentSpec(scrollerParams);
        RFPlotMatchStickSpec newSpec = new RFPlotMatchStickSpec(currentSpec);
        newSpec.setSpec(savedSpecs.get(currentSpecIndex).getMStickSpec());

        // Set the new spec and update the drawable
        scrollerParams.getRfPlotDrawable().setSpec(newSpec.toXml());
        scrollerParams.setNewValue("Rand Matchstick: " + (currentSpecIndex + 1));
        return scrollerParams;
    }
}