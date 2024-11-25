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

public class FourierBubble extends Bubble<FourierBubbleFactory.FrequencyComponent, FourierBubbleFactory.FrequencyComponent>{
    private FastFourierTransformer transformer = new FastFourierTransformer(DftNormalization.STANDARD);
    public FourierBubble(FourierBubbleFactory.FrequencyComponent location, FourierBubbleFactory.FrequencyComponent size, String imgPath) {
        super(location, size, imgPath);
    }

    @Override
    public void generateBubblePixels() throws IOException {
        BufferedImage image = ImageIO.read(new File(imgPath));
        int backgroundColor = getBackgroundColor(image);

        // Get foreground mask and pixels
        boolean[][] foregroundMask = new boolean[image.getHeight()][image.getWidth()];
        List<PixelLocation> foregroundPoints = new ArrayList<>();
        for (int y = 0; y < image.getHeight(); y++) {
            for (int x = 0; x < image.getWidth(); x++) {
                if (image.getRGB(x, y) != backgroundColor) {
                    foregroundMask[y][x] = true;
                    foregroundPoints.add(new PixelLocation(x, y));
                }
            }
        }

        // Convert foreground to grayscale and perform FFT
        double[][] grayscaleData = imageToGrayscale(image, foregroundMask);
        int padSize = nextPowerOf2(Math.max(grayscaleData.length, grayscaleData[0].length));
        double[][] paddedData = padToPowerOf2(grayscaleData, padSize);
        Complex[][] fftData = perform2DFFT(paddedData);
        double[][] magnitudeSpectrum = calculateMagnitudeSpectrum(fftData);


        for (PixelLocation p : foregroundPoints) {
            FourierBubbleFactory.FrequencyComponent pixelFreq = getDominantFrequency(p.x, p.y, magnitudeSpectrum);

            double noiseChance = calculate2DGaussian(
                    pixelFreq.frequency, pixelFreq.orientation,
                    location.frequency, location.orientation,
                    size.frequency, size.orientation
            );

            if (noiseChance > 0.1) {
                noisyPixels.add(new NoisyPixel(p.x, p.y, noiseChance));
            }
        }
    }

    private FourierBubbleFactory.FrequencyComponent getDominantFrequency(int x, int y, double[][] magnitudeSpectrum) {
        double maxMagnitude = 0;
        double dominantFreq = 0;
        double dominantOrientation = 0;

        int patchSize = 8;  // Look at 8x8 patch around pixel

        // Extract patch centered on pixel
        double[][] patch = new double[patchSize][patchSize];
        for(int i = 0; i < patchSize; i++) {
            for(int j = 0; j < patchSize; j++) {
                int pi = x + i - patchSize/2;
                int pj = y + j - patchSize/2;

                // Check bounds
                if(pi >= 0 && pi < magnitudeSpectrum.length &&
                        pj >= 0 && pj < magnitudeSpectrum[0].length) {
                    patch[i][j] = magnitudeSpectrum[pi][pj];
                }
            }
        }

        // Now find dominant frequency in this patch
        for(int i = 0; i < patchSize; i++) {
            for(int j = 0; j < patchSize; j++) {
                // Convert patch coordinates to frequency coordinates
                double di = (i - patchSize/2.0) / patchSize;  // Normalize to [-0.5, 0.5]
                double dj = (j - patchSize/2.0) / patchSize;

                double freq = Math.sqrt(di*di + dj*dj);  // Radial frequency
                if(freq > 0) {  // Ignore DC
                    double orientation = Math.atan2(dj, di);
                    double magnitude = patch[i][j];

                    if(magnitude > maxMagnitude) {
                        maxMagnitude = magnitude;
                        dominantFreq = freq;
                        dominantOrientation = orientation;
                    }
                }
            }
        }

        return new FourierBubbleFactory.FrequencyComponent(dominantFreq, dominantOrientation, maxMagnitude);
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