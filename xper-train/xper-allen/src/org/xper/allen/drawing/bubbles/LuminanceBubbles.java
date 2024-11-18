package org.xper.allen.drawing.bubbles;

import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public class LuminanceBubbles implements Bubbles {
    private Random random = new Random();

    @Override
    public List<BubblePixel> generateBubbles(String imagePath, int nBubbles, double bubbleSigmaPercent) {
        try {
            BufferedImage image = ImageIO.read(new File(imagePath));
            int backgroundColor = image.getRGB(0, 0);

            // Find luminance range in foreground
            double minLuminance = Double.MAX_VALUE;
            double maxLuminance = Double.MIN_VALUE;

            for (int x = 0; x < image.getWidth(); x++) {
                for (int y = 0; y < image.getHeight(); y++) {
                    if (image.getRGB(x, y) != backgroundColor) {
                        double luminance = getLuminance(new Color(image.getRGB(x, y)));
                        minLuminance = Math.min(minLuminance, luminance);
                        maxLuminance = Math.max(maxLuminance, luminance);
                    }
                }
            }

            double luminanceRange = maxLuminance - minLuminance;
            double sigma = luminanceRange * bubbleSigmaPercent;
            List<BubblePixel> bubblePixels = new ArrayList<>();

            // Generate nBubbles by choosing random luminance values
            for (int i = 0; i < nBubbles; i++) {
                // Pick random luminance value uniformly from the range
                double centerLuminance = minLuminance + (random.nextDouble() * luminanceRange);

                // Generate Gaussian bubble in luminance space
                generateLuminanceBubble(centerLuminance, sigma, image, backgroundColor, bubblePixels);
            }

            return bubblePixels;

        } catch (IOException e) {
            throw new RuntimeException("Failed to load image: " + imagePath, e);
        }
    }

    private void generateLuminanceBubble(double centerLuminance, double sigma,
                                         BufferedImage image, int backgroundColor,
                                         List<BubblePixel> pixels) {
        // Check all pixels in the image
        for (int x = 0; x < image.getWidth(); x++) {
            for (int y = 0; y < image.getHeight(); y++) {
                int pixelColor = image.getRGB(x, y);
                if (pixelColor == backgroundColor) {
                    continue;
                }

                double pixelLuminance = getLuminance(new Color(pixelColor));
                double luminanceDiff = Math.abs(pixelLuminance - centerLuminance);

                double noiseChance = Math.exp(
                        -(luminanceDiff * luminanceDiff) /
                                (2 * sigma * sigma)
                );

                if (noiseChance > 0.01) {
                    pixels.add(new BubblePixel(x, y, noiseChance));
                }
            }
        }
    }

    private double getLuminance(Color color) {
        return 0.2126 * color.getRed() +
                0.7152 * color.getGreen() +
                0.0722 * color.getBlue();
    }
}