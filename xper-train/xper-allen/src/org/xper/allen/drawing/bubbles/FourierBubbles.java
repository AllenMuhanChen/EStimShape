package org.xper.allen.drawing.bubbles;

import org.apache.commons.math3.complex.Complex;
import org.apache.commons.math3.transform.DftNormalization;
import org.apache.commons.math3.transform.FastFourierTransformer;
import org.apache.commons.math3.transform.TransformType;

import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public class FourierBubbles implements Bubbles {
    private static final int MIN_PIXELS_PER_BUBBLE = 100;
    private static final int MAX_ATTEMPTS_PER_BUBBLE = 10000;
    public static final double SIGNIFICANCE_THRESHOLD = 0.01;
    private Random random = new Random();
    private FastFourierTransformer transformer = new FastFourierTransformer(DftNormalization.STANDARD);

    private static class FrequencyComponent {
        final double frequency;
        final double orientation;
        final double magnitude;

        FrequencyComponent(double frequency, double orientation, double magnitude) {
            this.frequency = frequency;
            this.orientation = orientation;
            this.magnitude = magnitude;
        }
    }

    private static class FrequencyPoint {
        final double frequency;
        final double orientation;

        FrequencyPoint(double frequency, double orientation) {
            this.frequency = frequency;
            this.orientation = orientation;
        }
    }

    @Override
    public List<BubblePixel> generateBubbles(String imagePath, int nBubbles, double bubbleSigmaPercent) {
        try {
            BufferedImage image = ImageIO.read(new File(imagePath));
            int backgroundColor = image.getRGB(0, 0);

            // Get foreground mask and pixels
            boolean[][] foregroundMask = new boolean[image.getHeight()][image.getWidth()];
            List<Point> foregroundPoints = new ArrayList<>();
            for (int y = 0; y < image.getHeight(); y++) {
                for (int x = 0; x < image.getWidth(); x++) {
                    if (image.getRGB(x, y) != backgroundColor) {
                        foregroundMask[y][x] = true;
                        foregroundPoints.add(new Point(x, y));
                    }
                }
            }

            if (foregroundPoints.isEmpty()) {
                return new ArrayList<>();
            }

            // Convert foreground to grayscale and perform FFT
            double[][] grayscaleData = imageToGrayscale(image, foregroundMask);
            int padSize = nextPowerOf2(Math.max(grayscaleData.length, grayscaleData[0].length));
            double[][] paddedData = padToPowerOf2(grayscaleData, padSize);
            Complex[][] fftData = perform2DFFT(paddedData);
            double[][] magnitudeSpectrum = calculateMagnitudeSpectrum(fftData);

            // Find maximum magnitude to set threshold (excluding DC)
            double maxMagnitude = 0;
            int center = magnitudeSpectrum.length / 2;
            for (int i = 0; i < magnitudeSpectrum.length; i++) {
                for (int j = 0; j < magnitudeSpectrum[0].length; j++) {
                    if (!(i == center && j == center)) {  // Skip DC
                        maxMagnitude = Math.max(maxMagnitude, magnitudeSpectrum[i][j]);
                    }
                }
            }

            // Collect significant frequency points (above threshold)
            List<FrequencyPoint> significantPoints = new ArrayList<>();
            double magnitudeThreshold = maxMagnitude * SIGNIFICANCE_THRESHOLD; // Lower threshold to 1%
            double maxFreq = 0;

            // Scan frequency space relative to center
            for (int i = 0; i < magnitudeSpectrum.length; i++) {
                for (int j = 0; j < magnitudeSpectrum[0].length; j++) {
                    // Calculate frequency coordinates relative to center
                    int di = i - center;
                    int dj = j - center;
                    double freq = Math.sqrt(di*di + dj*dj);

                    if (freq > 0 && magnitudeSpectrum[i][j] > magnitudeThreshold) {
                        maxFreq = Math.max(maxFreq, freq);
                        double orientation = Math.atan2(dj, di);
                        significantPoints.add(new FrequencyPoint(freq, orientation));
                    }
                }
            }

            if (significantPoints.isEmpty()) {
                System.out.println("No significant points found!");
                return new ArrayList<>();
            }

            // Calculate sigmas
            double sigmaFreq = maxFreq * bubbleSigmaPercent;
            double sigmaOrientation = Math.PI * bubbleSigmaPercent;

            List<BubblePixel> allBubblePixels = new ArrayList<>();

            // Generate bubbles by sampling from significant points
            int successfulBubbles = 0;
            while (successfulBubbles < nBubbles) {
                List<BubblePixel> bubblePixels = new ArrayList<>();
                int attempts = 0;

                while (attempts < MAX_ATTEMPTS_PER_BUBBLE) {
                    bubblePixels.clear();

                    FrequencyPoint centerPoint = significantPoints.get(
                            random.nextInt(significantPoints.size())
                    );



                    for (Point p : foregroundPoints) {
                        FrequencyComponent pixelFreq = getDominantFrequency(p.x, p.y, magnitudeSpectrum, center);

                        double noiseChance = calculate2DGaussian(
                                pixelFreq.frequency, pixelFreq.orientation,
                                centerPoint.frequency, centerPoint.orientation,
                                sigmaFreq, sigmaOrientation
                        );

                        if (noiseChance > 0.01) {
                            bubblePixels.add(new BubblePixel(p.x, p.y, noiseChance));
                        }
                    }


                    if (bubblePixels.size() >= MIN_PIXELS_PER_BUBBLE) {
                        allBubblePixels.addAll(bubblePixels);
                        successfulBubbles++;
                        System.out.println("Tried bubble at freq=" + centerPoint.frequency +
                                ", orientation=" + centerPoint.orientation);
                        System.out.println("Successful bubble " + successfulBubbles + " placed");
                        System.out.println("Bubble affected " + bubblePixels.size() + " pixels");
                        break;
                    }

                    attempts++;
                }

                if (attempts == MAX_ATTEMPTS_PER_BUBBLE) {
                    System.out.println("Warning: Could not place bubble after " + MAX_ATTEMPTS_PER_BUBBLE +
                            " attempts with minimum " + MIN_PIXELS_PER_BUBBLE + " pixels");
                    break;
                }
            }

            return allBubblePixels;

        } catch (IOException e) {
            throw new RuntimeException("Failed to load image: " + imagePath, e);
        }
    }

    private double calculate2DGaussian(double pixelFreq, double pixelOrientation,
                                       double centerFreq, double centerOrientation,
                                       double sigmaFreq, double sigmaOrientation) {
        // Handle circular nature of orientation
        double orientationDiff = Math.min(
                Math.abs(pixelOrientation - centerOrientation),
                2 * Math.PI - Math.abs(pixelOrientation - centerOrientation)
        );

        // 2D gaussian
        return Math.exp(
                -(Math.pow(pixelFreq - centerFreq, 2) / (2 * sigmaFreq * sigmaFreq) +
                        Math.pow(orientationDiff, 2) / (2 * sigmaOrientation * sigmaOrientation))
        );
    }

    private FrequencyComponent getDominantFrequency(int x, int y, double[][] magnitudeSpectrum, int center) {
        int size = magnitudeSpectrum.length;
        double maxMagnitude = 0;
        double dominantFreq = 0;
        double dominantOrientation = 0;

        // Search local neighborhood in frequency domain
        int windowSize = 5;  // Increased window size
        for (int i = Math.max(0, x-windowSize); i <= Math.min(size-1, x+windowSize); i++) {
            for (int j = Math.max(0, y-windowSize); j <= Math.min(size-1, y+windowSize); j++) {
                // Calculate frequency coordinates relative to center
                int di = i - center;
                int dj = j - center;
                double freq = Math.sqrt(di*di + dj*dj);

                if (freq > 0) {
                    double orientation = Math.atan2(dj, di);
                    double magnitude = magnitudeSpectrum[i][j];

                    if (magnitude > maxMagnitude) {
                        maxMagnitude = magnitude;
                        dominantFreq = freq;
                        dominantOrientation = orientation;
                    }
                }
            }
        }

        return new FrequencyComponent(dominantFreq, dominantOrientation, maxMagnitude);
    }

    // Rest of the helper methods remain the same
    private double[][] imageToGrayscale(BufferedImage image, boolean[][] foregroundMask) {
        double[][] data = new double[image.getHeight()][image.getWidth()];
        for (int y = 0; y < image.getHeight(); y++) {
            for (int x = 0; x < image.getWidth(); x++) {
                if (foregroundMask[y][x]) {
                    Color c = new Color(image.getRGB(x, y));
                    data[y][x] = 0.2989 * c.getRed() +
                            0.5870 * c.getGreen() +
                            0.1140 * c.getBlue();
                }
            }
        }
        return data;
    }

    private double[][] padToPowerOf2(double[][] data, int size) {
        double[][] padded = new double[size][size];
        for (int i = 0; i < data.length; i++) {
            System.arraycopy(data[i], 0, padded[i], 0, data[i].length);
        }
        return padded;
    }

    private Complex[][] perform2DFFT(double[][] data) {
        int size = data.length;
        Complex[][] result = new Complex[size][size];

        // FFT rows
        for (int i = 0; i < size; i++) {
            Complex[] row = new Complex[size];
            for (int j = 0; j < size; j++) {
                row[j] = new Complex(data[i][j], 0);
            }
            Complex[] transformedRow = transformer.transform(row, TransformType.FORWARD);
            result[i] = transformedRow;
        }

        // FFT columns
        for (int j = 0; j < size; j++) {
            Complex[] col = new Complex[size];
            for (int i = 0; i < size; i++) {
                col[i] = result[i][j];
            }
            Complex[] transformedCol = transformer.transform(col, TransformType.FORWARD);
            for (int i = 0; i < size; i++) {
                result[i][j] = transformedCol[i];
            }
        }

        return result;
    }

    private double[][] calculateMagnitudeSpectrum(Complex[][] fftData) {
        int size = fftData.length;
        double[][] magnitude = new double[size][size];
        for (int i = 0; i < size; i++) {
            for (int j = 0; j < size; j++) {
                magnitude[i][j] = fftData[i][j].abs();
            }
        }
        return magnitude;
    }

    private int nextPowerOf2(int n) {
        return Integer.highestOneBit(n - 1) << 1;
    }
}