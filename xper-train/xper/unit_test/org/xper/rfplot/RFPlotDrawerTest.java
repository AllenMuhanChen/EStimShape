package org.xper.rfplot;

import org.junit.Test;
import org.xper.drawing.Coordinates2D;

import static org.junit.Assert.assertEquals;

public class RFPlotDrawerTest {

    @Test
    public void plotter_gets_center_of_rf(){
        RFPlotDrawer plotter = new RFPlotDrawer();

        Coordinates2D coords1 = new Coordinates2D(0,0);
        Coordinates2D coords2 = new Coordinates2D(10,0);
        Coordinates2D coords3 = new Coordinates2D(0,10);
        Coordinates2D coords4 = new Coordinates2D(10,10);
        plotter.add(coords1);
        plotter.add(coords2);
        plotter.add(coords3);
        plotter.add(coords4);
        Coordinates2D rfCenter = plotter.getRFCenter();

        assertEquals(new Coordinates2D(5,5), rfCenter);
    }
}
