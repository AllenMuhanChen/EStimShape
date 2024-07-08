package org.xper.allen.drawing.composition.noisy;

import org.junit.Before;
import org.junit.Test;
import org.xper.allen.drawing.composition.experiment.TwobyTwoMatchStick;
import org.xper.allen.drawing.ga.TestMatchStickDrawer;
import org.xper.util.ResourceUtil;

import javax.imageio.ImageIO;
import javax.swing.*;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.Arrays;

import static org.xper.drawing.TestDrawingWindow.initXperLibs;

public class GaussianNoiseMapperTest {

    private String testBin;
    private TestMatchStickDrawer drawer;
    private GaussianNoiseMapper gaussianNoiseMapper;

    @Before
    public void setUp() throws Exception {
        initXperLibs();
        testBin = ResourceUtil.getResource("testBin");

        drawer = new TestMatchStickDrawer();
        drawer.setup(190, 190);

        gaussianNoiseMapper = new GaussianNoiseMapper();
        gaussianNoiseMapper.setWidth(190);
        gaussianNoiseMapper.setHeight(190);
        gaussianNoiseMapper.setBackground(0); // Set background to black
    }

    @Test
    public void testGaussianNoiseMatchStickWithDifferentSpecialComps() throws IOException {
        // Generate a match stick with 3 components
        TwobyTwoMatchStick matchStick = new TwobyTwoMatchStick();
        matchStick.setProperties(8, "SHADE");
        matchStick.genMatchStickRand(3);

        // Test different combinations of special components
        java.util.List<java.util.List<Integer>> specialCompCombinations = Arrays.asList(
//                Arrays.asList(1),
//                Arrays.asList(2),
//                Arrays.asList(3),
                Arrays.asList(1, 2),
                Arrays.asList(1, 3),
                Arrays.asList(2, 3)
//                Arrays.asList(1, 2, 3)
        );

        for (java.util.List<Integer> specialComps : specialCompCombinations) {
            testGaussianNoiseForSpecialComps(matchStick, specialComps);
        }
    }

    private void testGaussianNoiseForSpecialComps(TwobyTwoMatchStick matchStick, java.util.List<Integer> specialComps) throws IOException {
        // Draw the original match stick
        drawer.clear();
        drawer.drawMStick(matchStick);
        String imagePath = drawer.saveImage(testBin + "/original_matchstick_" + specialComps.toString());

        // Generate Gaussian noise map
        String noiseMapPath = gaussianNoiseMapper.mapNoise(matchStick, 0.5, specialComps, drawer.window.renderer, testBin + "/gaussian_noise_map_" + specialComps.toString() + ".png");

        // Load original image and noise map
        BufferedImage originalImage = ImageIO.read(new File(imagePath));
        BufferedImage noiseMap = ImageIO.read(new File(noiseMapPath));

        // Apply noise manually
        BufferedImage noisyImage = applyNoise(originalImage, noiseMap);

        // Save noisy image
        ImageIO.write(noisyImage, "PNG", new File(testBin + "/noisy_matchstick_" + specialComps.toString() + ".png"));

        // Display noisy image
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
            Thread.sleep(5000);  // Display for 5 seconds
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        frame.dispose();
    }
}