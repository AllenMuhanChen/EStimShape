package org.xper.allen.monitorlinearization;

import org.junit.Test;

import static org.junit.Assert.*;

public class MonLinTrialGeneratorTest {

    @Test
    public void test_cyan_HSV() {
        float h = 180;
        float s = 1f;
        float v = 1f;


        //Full Bright Cyan
        int[] rgb = MonLinTrialGenerator.hsvToRgb(h, s, v);
        assertEquals(0, rgb[0]);
        assertEquals(255, rgb[1]);
        assertEquals(255, rgb[2]);

        float[] hsv = MonLinTrialGenerator.rgbToHsv(rgb[0], rgb[1], rgb[2]);
        assertEquals(h, hsv[0], 0.01);
        assertEquals(s, hsv[1], 0.01);
        assertEquals(v, hsv[2], 0.01);

        //Half Bright Cyan
        v = 0.5f;
        rgb = MonLinTrialGenerator.hsvToRgb(h, s, v);
        assertEquals(0, rgb[0]);
        assertEquals(127, rgb[1]);
        assertEquals(127, rgb[2]);

        hsv = MonLinTrialGenerator.rgbToHsv(rgb[0], rgb[1], rgb[2]);
        assertEquals(h, hsv[0], 0.01);
        assertEquals(s, hsv[1], 0.01);
        assertEquals(v, hsv[2], 0.01);

        //Zero Bright Cyan
        v = 0f;
        rgb = MonLinTrialGenerator.hsvToRgb(h, s, v);
        assertEquals(0, rgb[0]);
        assertEquals(0, rgb[1]);
        assertEquals(0, rgb[2]);






    }
}