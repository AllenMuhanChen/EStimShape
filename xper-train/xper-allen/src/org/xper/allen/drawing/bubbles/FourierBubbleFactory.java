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

public class FourierBubbleFactory implements BubbleFactory {
    private static final int MIN_PIXELS_PER_BUBBLE = 1;
    private static final int MAX_ATTEMPTS_PER_BUBBLE = 10000;
    public static final double SIGNIFICANCE_THRESHOLD = 0.01;
    private Random random = new Random();
    private FastFourierTransformer transformer = new FastFourierTransformer(DftNormalization.STANDARD);

    static class FrequencyComponent {
        final double frequency;
        final double orientation;
        final double magnitude;

        FrequencyComponent(double frequency, double orientation, double magnitude) {
            this.frequency = frequency;
            this.orientation = orientation;
            this.magnitude = magnitude;
        }
    }

    @Override
    public List<Bubble> generateBubbles(String imagePath, int nBubbles, double bubbleSigmaPercent) {
        List<Bubble> bubbles = new ArrayList<>();
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

            // Find frequency range in FFT
            double maxMagnitude = 0;
            double minFreq = Double.MAX_VALUE;
            double maxFreq = 0;
            int center = magnitudeSpectrum.length / 2;

            // First find max magnitude
            for (int i = 0; i < magnitudeSpectrum.length; i++) {
                for (int j = 0; j < magnitudeSpectrum[0].length; j++) {
                    if (!(i == center && j == center)) {  // Skip DC
                        maxMagnitude = Math.max(maxMagnitude, magnitudeSpectrum[i][j]);
                    }
                }
            }

            // Then find frequency range of significant components
            double magnitudeThreshold = maxMagnitude * SIGNIFICANCE_THRESHOLD;
            for (int i = 0; i < magnitudeSpectrum.length; i++) {
                for (int j = 0; j < magnitudeSpectrum[0].length; j++) {
                    int di = i - center;
                    int dj = j - center;
                    double freq = Math.sqrt(di*di + dj*dj);

                    if (freq > 0 && magnitudeSpectrum[i][j] > magnitudeThreshold) {
                        minFreq = Math.min(minFreq, freq);
                        maxFreq = Math.max(maxFreq, freq);
                    }
                }
            }

            if (maxFreq == 0) {
                System.out.println("No significant frequencies found!");
                return new ArrayList<>();
            }

            // Calculate sigmas
            double freqRange = maxFreq - minFreq;
            double sigmaFreq = freqRange * bubbleSigmaPercent;
            double sigmaOrientation = Math.PI * bubbleSigmaPercent;

            List<NoisyPixel> allNoisyPixels = new ArrayList<>();

            // Generate bubbles by sampling uniformly
            int successfulBubbles = 0;
            while (successfulBubbles < nBubbles) {
                List<NoisyPixel> noisyPixels = new ArrayList<>();
                int attempts = 0;

                while (attempts < MAX_ATTEMPTS_PER_BUBBLE) {
                    noisyPixels.clear();

                    // Choose random frequency and orientation uniformly
                    double centerFreq = minFreq + (random.nextDouble() * freqRange);
                    double centerOrientation = random.nextDouble() * 2 * Math.PI - Math.PI;

                    FourierBubble bubble = new FourierBubble(new FrequencyComponent(centerFreq, centerOrientation, 0),
                            new FrequencyComponent(sigmaFreq, sigmaOrientation, 0), imagePath);
                    bubble.generateBubblePixels();
                    bubbles.add(bubble);
                    noisyPixels.addAll(bubble.getBubblePixels());

                    if (noisyPixels.size() >= MIN_PIXELS_PER_BUBBLE) {
                        allNoisyPixels.addAll(noisyPixels);
                        successfulBubbles++;
                        System.out.println("Bubble at freq=" + centerFreq +
                                ", orientation=" + centerOrientation);
                        System.out.println("Successful bubble " + successfulBubbles + " placed");
                        System.out.println("Bubble affected " + noisyPixels.size() + " pixels");
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

            return bubbles;

        } catch (IOException e) {
            throw new RuntimeException("Failed to load image: " + imagePath, e);
        }
    }

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