package org.xper.allen.drawing.bubbles;

import org.junit.Before;
import org.junit.Test;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.util.ResourceUtil;

import javax.imageio.ImageIO;
import javax.swing.*;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;

public class BubbleNoiseMapperTest {
    private String testImagePath;
    private String outputPathBubbles;
    private AbstractRenderer renderer;

    @Before
    public void setUp() throws Exception {
        String testBin = ResourceUtil.getResource("testBin");
        testImagePath = testBin + "/bubbles_test_img.png";
        outputPathBubbles = testBin + "/bubbles_noise_output.png";
    }

    @Test
    public void bubble_noise_mapper_generates_noise() throws IOException {
        // Arrange
        BubbleNoiseMapper mapper = new BubbleNoiseMapper();

        // Try different types of bubbles
//        testBubbles("Gaussian Bubbles", new GaussianBubbles(), 20, 1.0);
//        testBubbles("Luminance Bubbles", new LuminanceBubbles(), 3, 0.1);
        testBubbles("Fourier Bubbles", new FourierBubbles(), 3, 0.1);

        // Keep window open to examine results
        try {
            Thread.sleep(10000);  // 10 seconds to examine
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }

    private void testBubbles(String title, Bubbles bubbles, int nBubbles, double sigma) throws IOException {
        // Generate noise map
        BubbleNoiseMapper mapper = new BubbleNoiseMapper();
        String outputPath = outputPathBubbles.replace(".png", "_" + title.toLowerCase().replace(" ", "_") + ".png");
        String resultPath = mapper.mapNoise(testImagePath, bubbles, nBubbles, sigma, outputPath);

        // Display results
        BufferedImage originalImage = ImageIO.read(new File(testImagePath));
        BufferedImage noiseImage = ImageIO.read(new File(resultPath));

        JFrame frame = new JFrame(title);
        frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE);

        JPanel panel = new JPanel() {
            @Override
            protected void paintComponent(Graphics g) {
                super.paintComponent(g);
                // Draw original image on left
                g.drawImage(originalImage, 0, 0, this);
                // Draw noise image on right
                g.drawImage(noiseImage, originalImage.getWidth() + 10, 0, this);
            }
        };

        panel.setPreferredSize(new Dimension(
                (originalImage.getWidth() * 2) + 10,
                originalImage.getHeight()
        ));

        frame.add(panel);
        frame.pack();
        frame.setVisible(true);
    }
}