package org.xper.allen.drawing.bubbles;

import org.junit.Before;
import org.junit.Test;
import org.xper.util.ResourceUtil;

import javax.imageio.ImageIO;
import javax.swing.*;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class BubbleFactoryTest {
    private String testImagePath;
    private String outputPath;
    private String outputPathLuminance;

    @Before
    public void setUp() throws Exception {
        String testBin = ResourceUtil.getResource("testBin");
        testImagePath = testBin + "/bubbles_test_img.png";
        outputPath = testBin + "/bubbles_output.png";
        outputPathLuminance = testBin + "/bubbles_luminance_output.png";
    }

    @Test
    public void cartesian_bubbles_generates_bubbles() throws IOException {
        // Arrange
        CartesianBubbleFactory cartesianBubbles = new CartesianBubbleFactory();
        int nBubbles = 5;
        double bubbleSigma = 5.0;
        List<Bubble> bubbles = cartesianBubbles.generateBubbles(testImagePath, nBubbles, bubbleSigma);

        // Act and visualize
        visualizeBubbles(bubbles, outputPath, "Gaussian Bubbles");
    }

    @Test
    public void luminance_bubbles_generates_bubbles() throws IOException {
        // Arrange
        BubbleFactory luminanceBubbleFactory = new LuminanceBubbleFactory();
        int nBubbles = 3;
        double bubbleSigma = 0.1/3;
        List<Bubble> bubbles = luminanceBubbleFactory.generateBubbles(testImagePath, nBubbles, bubbleSigma);

        // Act and visualize
        visualizeBubbles(bubbles, outputPathLuminance, "Luminance Bubbles");
    }

    @Test
    public void fourier_bubbles_generates_bubbles() throws IOException {
        // Arrange
        BubbleFactory fourierBubbleFactory = new FourierBubbleFactory();
        int nBubbles = 5;
        double bubbleSigma = 0.2/3.0;
        List<Bubble> bubbles = fourierBubbleFactory.generateBubbles(testImagePath, nBubbles, bubbleSigma);

        // Act and visualize
        visualizeBubbles(bubbles, outputPath, "Spatial Frequency Bubbles");
    }

    private void visualizeBubbles(List<Bubble> bubbles, String outputPath, String windowTitle)
            throws IOException {
        // Generate bubbles
        List<NoisyPixel> noisyPixels = new ArrayList<>();
        for (Bubble bubble : bubbles) {
            bubble.generateBubblePixels();
            noisyPixels.addAll(bubble.getNoisyPixels());
        }

        // Load original image
        BufferedImage originalImage = ImageIO.read(new File(testImagePath));
        BufferedImage outputImage = new BufferedImage(
                originalImage.getWidth(),
                originalImage.getHeight(),
                BufferedImage.TYPE_INT_ARGB  // Changed to support alpha
        );

        // Copy original image
        for (int x = 0; x < originalImage.getWidth(); x++) {
            for (int y = 0; y < originalImage.getHeight(); y++) {
                outputImage.setRGB(x, y, originalImage.getRGB(x, y));
            }
        }

        // Set bubble pixels - now using alpha for noise chance
        for (NoisyPixel pixel : noisyPixels) {
            // Convert noise chance to alpha (0-255)
            int alpha = (int)(255 * pixel.noiseChance);
            Color pixelColor = new Color(255, 0, 0, alpha);  // Full red with variable alpha

            // Get original pixel color
            Color originalColor = new Color(outputImage.getRGB(pixel.x, pixel.y), true);

            // Blend the colors based on alpha
            float blendFactor = alpha / 255f;
            int r = (int)((pixelColor.getRed() * blendFactor) + (originalColor.getRed() * (1 - blendFactor)));
            int g = (int)((pixelColor.getGreen() * blendFactor) + (originalColor.getGreen() * (1 - blendFactor)));
            int b = (int)((pixelColor.getBlue() * blendFactor) + (originalColor.getBlue() * (1 - blendFactor)));

            Color blendedColor = new Color(r, g, b);
            outputImage.setRGB(pixel.x, pixel.y, blendedColor.getRGB());
        }

        // Save output image
        ImageIO.write(outputImage, "PNG", new File(outputPath));

        // Display in window
        JFrame frame = new JFrame(windowTitle);
        frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE);

        // Create a panel that shows both original and output images side by side
        JPanel panel = new JPanel() {
            @Override
            protected void paintComponent(Graphics g) {
                super.paintComponent(g);
                // Draw original image on left
                g.drawImage(originalImage, 0, 0, this);
                // Draw output image on right
                g.drawImage(outputImage, originalImage.getWidth() + 10, 0, this);
            }
        };

        // Set panel size to fit both images
        panel.setPreferredSize(new Dimension(
                (originalImage.getWidth() * 2) + 10,
                originalImage.getHeight()
        ));

        frame.add(panel);
        frame.pack();
        frame.setVisible(true);

        // Keep window open for viewing
        try {
            Thread.sleep(20000);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }
}