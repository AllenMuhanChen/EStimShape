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

public class SpatialFrequencyBubbles implements Bubbles {
    private Random random = new Random();
    private FastFourierTransformer transformer = new FastFourierTransformer(DftNormalization.STANDARD);

    private static class FrequencyComponent {
        final double frequency;    // Radial distance from DC
        final double orientation;  // Angle in radians [-π, π]
        final double magnitude;    // Strength of this component

        FrequencyComponent(double frequency, double orientation, double magnitude) {
            this.frequency = frequency;
            this.orientation = orientation;
            this.magnitude = magnitude;
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

            // Find active frequency ranges in foreground FFT
            double minActiveFreq = Double.MAX_VALUE;
            double maxActiveFreq = 0;
            double significantMagnitudeThreshold = 0.01;  // Threshold to consider a frequency "active"

            // First pass: find maximum magnitude to set relative threshold
            double maxMagnitude = 0;
            for (int i = 0; i < magnitudeSpectrum.length/2; i++) {
                for (int j = 0; j < magnitudeSpectrum[0].length/2; j++) {
                    maxMagnitude = Math.max(maxMagnitude, magnitudeSpectrum[i][j]);
                }
            }

            // Set threshold relative to maximum magnitude
            significantMagnitudeThreshold = maxMagnitude * 0.01;  // Consider frequencies with >1% of max magnitude

            // Second pass: find active frequency range
            for (int i = 0; i < magnitudeSpectrum.length/2; i++) {
                for (int j = 0; j < magnitudeSpectrum[0].length/2; j++) {
                    double freq = Math.sqrt(i*i + j*j);
                    if (freq > 0 && magnitudeSpectrum[i][j] > significantMagnitudeThreshold) {
                        minActiveFreq = Math.min(minActiveFreq, freq);
                        maxActiveFreq = Math.max(maxActiveFreq, freq);
                    }
                }
            }

            if (maxActiveFreq == 0 || minActiveFreq == Double.MAX_VALUE) {
                return new ArrayList<>();  // No significant frequencies found
            }

            // Calculate sigmas based on active frequency range
            double activeFreqRange = maxActiveFreq - minActiveFreq;
            double sigmaFreq = activeFreqRange * bubbleSigmaPercent;
            double sigmaOrientation = Math.PI * bubbleSigmaPercent;

            List<BubblePixel> bubblePixels = new ArrayList<>();

            // Generate bubbles in frequency-orientation space
            for (int b = 0; b < nBubbles; b++) {
                // Choose random center from active frequency range
                double centerFreq = minActiveFreq + (random.nextDouble() * activeFreqRange);
                double centerOrientation = random.nextDouble() * 2 * Math.PI - Math.PI; // [-π, π]

                // Calculate dominant frequency components for each foreground pixel
                for (Point p : foregroundPoints) {
                    FrequencyComponent pixelFreq = getDominantFrequency(p.x, p.y, magnitudeSpectrum);

                    // Only process pixels with significant frequency components
                    if (pixelFreq.magnitude > significantMagnitudeThreshold) {
                        double noiseChance = calculate2DGaussian(
                                pixelFreq.frequency, pixelFreq.orientation,
                                centerFreq, centerOrientation,
                                sigmaFreq, sigmaOrientation
                        );

                        if (noiseChance > 0.01) {
                            bubblePixels.add(new BubblePixel(p.x, p.y, noiseChance));
                        }
                    }
                }
            }

            return bubblePixels;

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

    private FrequencyComponent getDominantFrequency(int x, int y, double[][] magnitudeSpectrum) {
        int size = magnitudeSpectrum.length;
        double maxMagnitude = 0;
        double dominantFreq = 0;
        double dominantOrientation = 0;

        // Search local neighborhood in frequency domain
        int windowSize = 3;
        for (int i = Math.max(0, x-windowSize); i <= Math.min(size-1, x+windowSize); i++) {
            for (int j = Math.max(0, y-windowSize); j <= Math.min(size-1, y+windowSize); j++) {
                double freq = Math.sqrt(i*i + j*j);
                if (freq > 0) {  // Ignore DC
                    double orientation = Math.atan2(j, i);  // [-π, π]
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

    // Helper methods remain the same
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