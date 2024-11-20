package org.xper.allen.drawing.bubbles;

import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class LuminanceBubble extends Bubble<Double, Double>{
    public LuminanceBubble(Double location, Double size, String imgPath) {
        super(location, size, imgPath);
    }

    @Override
    public void generateBubblePixels() throws IOException {
        BufferedImage image = ImageIO.read(new File(imgPath));
        int backgroundColor = getBackgroundColor(image);
        this.noisyPixels = generateLuminanceBubble(location, size, image, backgroundColor);
    }

    private List<NoisyPixel> generateLuminanceBubble(double centerLuminance, double sigma,
                                                     BufferedImage image, int backgroundColor) {

        List<NoisyPixel> pixels = new ArrayList<>();
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
                    pixels.add(new NoisyPixel(x, y, noiseChance));
                }
            }
        }
        return pixels;
    }

    private double getLuminance(Color color) {
        return 0.2126 * color.getRed() +
                0.7152 * color.getGreen() +
                0.0722 * color.getBlue();
    }
}