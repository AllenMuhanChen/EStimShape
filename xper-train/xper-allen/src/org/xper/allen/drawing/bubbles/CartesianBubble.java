package org.xper.allen.drawing.bubbles;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class CartesianBubble extends Bubble<PixelLocation, Double>{

    public CartesianBubble(PixelLocation location, Double size, String imgPath) {
        super(location, size, imgPath);
    }

    @Override
    public void generateBubblePixels() throws IOException {;
        BufferedImage image = ImageIO.read(new File(imgPath));
        this.noisyPixels = generateCircleBubble(location, size, image.getWidth(), image.getHeight());
    }

    private List<NoisyPixel> generateCircleBubble(PixelLocation center, double radius, int width, int height){
        List<NoisyPixel> pixels = new ArrayList<>();
        int range = (int) Math.ceil(radius);
        for (int x = center.x - range; x <= center.x + range; x++) {
            for (int y = center.y - range; y <= center.y + range; y++) {
                if (x < 0 || x >= width || y < 0 || y >= height) {
                    continue;
                }
                double distance = Math.sqrt(
                        Math.pow(x - center.x, 2) +
                                Math.pow(y - center.y, 2)
                );
                if (distance <= radius) {
                    pixels.add(new NoisyPixel(x, y, 1.0));
                }
            }
        }
        return pixels;
    }

    private List<NoisyPixel> generateGaussianBubble(PixelLocation center, double sigma, int width, int height) {
        List<NoisyPixel> pixels = new ArrayList<>();

        int range = (int) Math.ceil(4 * sigma);

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
        return pixels;
    }

}