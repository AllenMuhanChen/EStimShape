package org.xper.allen.rfplot;

import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.DefaultSpecRFPlotDrawable;

public class RFPlotMatchStick extends DefaultSpecRFPlotDrawable {
    AllenMatchStick matchStick;
    double sizeDiameterDegrees = 10;

    public RFPlotMatchStick() {
        setDefaultSpec();
    }

    @Override
    public void draw(Context context) {
        matchStick.draw();
    }

    @Override
    public void setSpec(String spec) {

    }

    @Override
    public void setDefaultSpec() {
        matchStick = new AllenMatchStick();
        matchStick.setProperties(sizeDiameterDegrees, "SHADE");
        matchStick.genMatchStickRand();
        System.out.println("MatchStick: " + matchStick.toString());
    }

    @Override
    public String getSpec() {
        return null;
    }

    @Override
    public void projectCoordinates(Coordinates2D mouseCoordinates) {

    }
}