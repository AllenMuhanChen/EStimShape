package org.xper.allen.drawing.gabor;

import org.junit.Test;
import org.xper.rfplot.drawing.gabor.ColourConverter;

import java.awt.*;

public class ColorConverterTest {

    @Test
    public void RGBtoLab() {
        double[] lab = ColourConverter.getLab(
                new Color(255, 0, 0),
                ColourConverter.WhitePoint.D50);

        System.out.println("L: " + lab[0] + " a: " + lab[1] + " b: " + lab[2]);
    }
}