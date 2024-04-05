package org.xper.rfplot.drawing;

import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.renderer.AbstractRenderer;

import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

public class RFPlotBlankObject implements RFPlotDrawable {
    @Override
    public void draw(Context context) {

    }

    @Override
    public void setSpec(String spec) {

    }

    @Override
    public void setDefaultSpec() {

    }

    @Override
    public String getSpec() {
        return "";
    }

    @Override
    public List<Coordinates2D> getOutlinePoints(AbstractRenderer renderer) {

        return new LinkedList<>();
    }

}