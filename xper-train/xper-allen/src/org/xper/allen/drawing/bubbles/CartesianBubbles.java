package org.xper.allen.drawing.bubbles;

import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public class CartesianBubbles implements Bubbles {
    private Random random = new Random();

    @Override
    public List<Bubble> generateBubbles(String imagePath, int nBubbles, double bubbleSigma) {
        try {
            List<Bubble> bubbles = new ArrayList<>();
            BufferedImage image = ImageIO.read(new File(imagePath));

            // Get background color (assume top-left pixel is background)
            int backgroundColor = image.getRGB(0, 0);

            // Create foreground mask and find valid pixel positions
            List<PixelLocation> foregroundPixels = new ArrayList<>();
            for (int x = 0; x < image.getWidth(); x++) {
                for (int y = 0; y < image.getHeight(); y++) {
                    if (image.getRGB(x, y) != backgroundColor) {
                        foregroundPixels.add(new PixelLocation(x, y));
                    }
                }
            }

            if (foregroundPixels.isEmpty()) {
                return new ArrayList<>(); // No foreground pixels found
            }

            List<NoisyPixel> noisyPixels = new ArrayList<>();

            // Generate nBubbles centers in foreground
            for (int i = 0; i < nBubbles; i++) {
                // Pick random foreground pixel as center
                PixelLocation center = foregroundPixels.get(random.nextInt(foregroundPixels.size()));

                // Generate Gaussian bubble around center
                CartesianBubble bubble = new CartesianBubble(center, bubbleSigma, imagePath);
                bubble.generateBubblePixels();
                bubbles.add(bubble);
                noisyPixels.addAll(bubble.getBubblePixels());
            }

            return bubbles;

        } catch (IOException e) {
            throw new RuntimeException("Failed to load image: " + imagePath, e);
        }
    }

    private void generateGaussianBubble(Point center, double sigma, int width, int height, List<NoisyPixel> pixels) {
        // Calculate range to check (3 sigma covers 99.7% of distribution)
        int range = (int) Math.ceil(3 * sigma);

        // Generate pixels in square around center
        for (int x = center.x - range; x <= center.x + range; x++) {
            for (int y = center.y - range; y <= center.y + range; y++) {
                // Skip if outside image bounds
                if (x < 0 || x >= width || y < 0 || y >= height) {
                    continue;
                }

                // Calculate distance from center
                double distance = Math.sqrt(
                        Math.pow(x - center.x, 2) +
                                Math.pow(y - center.y, 2)
                );

                // Calculate Gaussian probability
                double noiseChance = Math.exp(
                        -(distance * distance) /
                                (2 * sigma * sigma)
                );

                // Add pixel if noise chance is significant
                if (noiseChance > 0.01) {  // Threshold to avoid too many tiny values
                    pixels.add(new NoisyPixel(x, y, noiseChance));
                }
            }
        }
    }
}