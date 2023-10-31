package org.xper.allen.drawing.composition.noisy;

import org.junit.Before;
import org.junit.Test;
import org.xper.util.ResourceUtil;
import org.xper.util.ThreadUtil;

import javax.imageio.ImageIO;
import javax.swing.*;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;

import static org.junit.Assert.*;

public class GaussianNoiseMapCalculationTest {

    private String testBin;

    @Before
    public void setUp() throws Exception {
        testBin = ResourceUtil.getResource("testBin");
    }

    @Test
    public void testGenerateGaussianNoiseMap() throws IOException {
        int width = 100;
        int height = 100;
        double centerX = 50;
        double centerY = 50;
        double sigmaX = 15;
        double sigmaY = 15;
        double amplitude = 1.0;

        BufferedImage noiseMap = GaussianNoiseMapCalculation.generateGaussianNoiseMap(width, height,
                centerX, centerY,
                sigmaX, sigmaY,
                amplitude);

        // Assertions
        assertEquals(width, noiseMap.getWidth());
        assertEquals(height, noiseMap.getHeight());

        // Check the center pixel (should have the highest intensity, i.e., redValue = 255)
        Color centerColor = new Color(noiseMap.getRGB((int)centerX, (int)centerY));
        assertEquals(255, centerColor.getRed());

        // Check a corner pixel (should have a lower intensity due to Gaussian drop-off)
        Color cornerColor = new Color(noiseMap.getRGB(0, 0));
        assertTrue(cornerColor.getRed() < 255);

        // Visualize the noise map
        JFrame frame = new JFrame();
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setSize(width + 50, height + 50);
        frame.add(new JLabel(new ImageIcon(noiseMap)));
        frame.setVisible(true);

        // Save the noise map to a PNG file
        File outputfile = new File(testBin, "noiseMap.png");
        ImageIO.write(noiseMap, "png", outputfile);

        ThreadUtil.sleep(1000);
    }
}