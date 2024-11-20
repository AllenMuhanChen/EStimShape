package org.xper.allen.drawing.bubbles;

import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class BubbleNoiseMapper {
    private static final double DEFAULT_THRESHOLD = 0.01;

    public String mapNoise(String imgPath,
                           BubbleFactory bubbleFactory,
                           int numBubbles,
                            double bubbleSigma,
                           String outputPath) {
        List<Bubble> bubbles = bubbleFactory.generateBubbles(imgPath, numBubbles, bubbleSigma);
        return mapNoise(imgPath, bubbles, outputPath);
    }

    public String mapNoise(String imgPath,
                           List<Bubble> bubbles,
                           String outputPath) {
        try {
            // Get dimensions from input image
            BufferedImage inputImage = ImageIO.read(new File(imgPath));
            int width = inputImage.getWidth();
            int height = inputImage.getHeight();

            // Generate bubbles
            List<NoisyPixel> bubblePixels = new ArrayList<>();
            for (Bubble bubble : bubbles) {
                bubble.generateBubblePixels();
                bubblePixels.addAll(bubble.getBubblePixels());
            }

            // Create noise map image
            BufferedImage noiseMap = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);

            // Fill with background
            Graphics2D g = noiseMap.createGraphics();
            g.setColor(new Color(0, 0, 0, 255));
            g.fillRect(0, 0, width, height);
            g.dispose();

            // Set bubble pixels in red channel
            for (NoisyPixel pixel : bubblePixels) {
                if (pixel.x >= 0 && pixel.x < width && pixel.y >= 0 && pixel.y < height) {
                    // Convert noise chance to red intensity (0-255)
                    int redValue = (int)(255 * pixel.noiseChance);
                    // Create color with only red channel and full alpha
                    Color pixelColor = new Color(redValue, 0, 0, 255);
                    noiseMap.setRGB(pixel.x, pixel.y, pixelColor.getRGB());
                }
            }

            // Save the noise map
            File outputFile = new File(outputPath);
            ImageIO.write(noiseMap, "png", outputFile);

            return outputFile.getAbsolutePath();

        } catch (IOException e) {
            throw new RuntimeException("Failed to process image: " + imgPath, e);
        }
    }
}