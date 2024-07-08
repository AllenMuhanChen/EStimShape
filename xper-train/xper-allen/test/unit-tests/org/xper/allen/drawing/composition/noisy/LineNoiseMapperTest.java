package org.xper.allen.drawing.composition.noisy;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.experiment.TwobyTwoMatchStick;
import org.xper.allen.drawing.ga.TestMatchStickDrawer;
import org.xper.allen.drawing.composition.noisy.LineNoiseMapper;
import org.xper.allen.noisy.NoisyTranslatableResizableImages;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveRenderer;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.util.FileUtil;
import org.xper.util.ResourceUtil;
import org.xper.util.ThreadUtil;

import javax.imageio.ImageIO;
import javax.swing.*;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.Collections;

import static org.xper.drawing.TestDrawingWindow.initXperLibs;

public class LineNoiseMapperTest {

    private String testBin;
    private AllenPNGMaker pngMaker;
    private TestMatchStickDrawer drawer;
    private LineNoiseMapper lineNoiseMapper;

    @Before
    public void setUp() throws Exception {
        initXperLibs();
        testBin = ResourceUtil.getResource("testBin");

        drawer = new TestMatchStickDrawer();
        drawer.setup(190, 190);

        lineNoiseMapper = new LineNoiseMapper();
        lineNoiseMapper.setWidth(190);
        lineNoiseMapper.setHeight(190);
        lineNoiseMapper.setBackground(0); // Set background to black
    }

    @Test
    public void testLineNoiseMatchStick() throws IOException {
        // Generate a match stick
        TwobyTwoMatchStick matchStick = new TwobyTwoMatchStick();
        matchStick.setProperties(8, "SHADE");
        matchStick.genMatchStickRand(2);

        // Draw the original match stick
        drawer.clear();
        drawer.drawMStick(matchStick);
        String imagePath = drawer.saveImage(testBin + "/original_matchstick");

        // Generate line noise map
        String noiseMapPath = lineNoiseMapper.mapNoise(matchStick, 0.5, 1, drawer.window.renderer, testBin + "/line_noise_map.png");

        // Load original image and noise map
        BufferedImage originalImage = ImageIO.read(new File(imagePath));
        BufferedImage noiseMap = ImageIO.read(new File(noiseMapPath));

        // Apply noise manually
        BufferedImage noisyImage = applyNoise(originalImage, noiseMap);

        // Save noisy image
        ImageIO.write(noisyImage, "PNG", new File(testBin + "/noisy_matchstick.png"));

        // Display noisy image (you'll need to implement this method)
        displayImage(noisyImage);
    }

    private BufferedImage applyNoise(BufferedImage original, BufferedImage noise) {
        int width = original.getWidth();
        int height = original.getHeight();
        BufferedImage result = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);

        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                int origColor = original.getRGB(x, y);
                int noiseColor = noise.getRGB(x, y);

                // Extract alpha channel from original image
                int alpha = (origColor >> 24) & 0xff;

                // Apply noise to RGB channels
                int red = Math.min(255, ((origColor >> 16) & 0xff) + ((noiseColor >> 16) & 0xff));
                int green = Math.min(255, ((origColor >> 8) & 0xff) + ((noiseColor >> 8) & 0xff));
                int blue = Math.min(255, (origColor & 0xff) + (noiseColor & 0xff));

                // Combine channels
                int newColor = (alpha << 24) | (red << 16) | (green << 8) | blue;
                result.setRGB(x, y, newColor);
            }
        }

        return result;
    }


    private void displayImage(BufferedImage image) {
        JFrame frame = new JFrame();
        JLabel label = new JLabel(new ImageIcon(image));
        frame.getContentPane().add(label, BorderLayout.CENTER);
        frame.pack();
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setVisible(true);

        // Wait for the user to close the window
        try {
            Thread.sleep(50000);  // Display for 5 seconds
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        frame.dispose();
    }
}