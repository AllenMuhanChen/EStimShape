package org.xper.allen.drawing.composition.noisy;

import org.xper.alden.drawing.renderer.AbstractRenderer;
import org.xper.allen.drawing.composition.AllenMAxisArc;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.AllenTubeComp;
import org.xper.drawing.Coordinates2D;

import javax.vecmath.Point3d;
import java.awt.Color;
import java.awt.image.BufferedImage;
import java.util.List;

public class GaussianNoiseMapCalculation {

    public static final double NOISE_RADIUS = 10;

    public static BufferedImage generateGaussianNoiseMapFor(AllenMatchStick mStick,
                                                            int width, int height,
                                                            double sigmaX, double sigmaY,
                                                            double amplitude, double background,
                                                            AbstractRenderer renderer){
        List<Integer> specialEnds = mStick.getSpecialEndComp();
        for (Integer compIndx: specialEnds){
            Point3d point3d = mStick.getComp()[compIndx].getmAxisInfo().getmPts()[26];
            AllenTubeComp allenTubeComp = mStick.getComp()[compIndx];
            AllenMAxisArc arc = allenTubeComp.getmAxisInfo();
            double mm_x = renderer.deg2mm(point3d.x);
            double mm_y = renderer.deg2mm(point3d.y);
            Coordinates2D world_x_y = renderer.coord2pixel(new Coordinates2D(mm_x, mm_y));

            double scaledX = world_x_y.getX();
            double scaledY = world_x_y.getY();


            return GaussianNoiseMapCalculation.generateTruncatedGaussianNoiseMap(width, height,
                    scaledX, scaledY,
                    NOISE_RADIUS, amplitude,
                    sigmaX, sigmaY,
                     background);
        }
        return null;
    }

    /**
     * Generates a noise map with a truncated Gaussian effect.
     *
     * @param width           Width of the noise map.
     * @param height          Height of the noise map.
     * @param centerX         X-coordinate of the circle center.
     * @param centerY         Y-coordinate of the circle center.
     * @param circleRadius    Radius of the circle.
     * @param noiseLevel      Noise level within the circle (0-1 range).
     * @param sigmaX          Standard deviation in the x direction for Gaussian outside the circle.
     * @param sigmaY          Standard deviation in the y direction for Gaussian outside the circle.
     * @param background      Background intensity (0 for black, 1 for red).
     * @return A noise map based on the truncated Gaussian effect.
     */
    public static BufferedImage generateTruncatedGaussianNoiseMap(int width, int height,
                                                                  double centerX, double centerY,
                                                                  double circleRadius, double noiseLevel,
                                                                  double sigmaX, double sigmaY,
                                                                  double background) {
        BufferedImage noiseMap = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);

        // Convert the background and noiseLevel values to a 0-255 range for the red component
        int backgroundRed = (int) (Math.min(background, 1.0) * 255);
        int noiseLevelRed = (int) (Math.min(noiseLevel, 1.0) * 255);

        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                double distanceToCenter = Math.sqrt(Math.pow(x - centerX, 2) + Math.pow(y - centerY, 2));

                int redValue = backgroundRed;

                if (distanceToCenter <= circleRadius) {
                    // Within the circle
                    redValue += noiseLevelRed;
                } else {
                    // Calculate Gaussian fade from the circle's edge
                    double offsetDistance = distanceToCenter - circleRadius;
                    double gaussValue = noiseLevel * Math.exp(-0.5 * (Math.pow(offsetDistance / sigmaX, 2) + Math.pow(offsetDistance / sigmaY, 2)));
                    redValue += (int) (Math.min(gaussValue, 1.0) * 255);
                }

                redValue = Math.min(redValue, 255);  // Ensure the value doesn't exceed 255

                // Set the pixel color in the noise map
                Color color = new Color(redValue, 0, 0, 255);
                noiseMap.setRGB(x, y, color.getRGB());
            }
        }
        return noiseMap;
    }

    /**
     * Generates a Gaussian noise map based on the specified parameters.
     *
     * @param width       Width of the noise map.
     * @param height      Height of the noise map.
     * @param centerX     X-coordinate of the Gaussian center.
     * @param centerY     Y-coordinate of the Gaussian center.
     * @param sigmaX      Standard deviation in the x direction.
     * @param sigmaY      Standard deviation in the y direction.
     * @param amplitude   Peak value of the Gaussian (0-1 range).
     * @param background  Background intensity (0 for black, 1 for red).
     * @return A noise map based on the Gaussian function.
     */
    public static BufferedImage generateGaussianNoiseMap(int width, int height,
                                                         double centerX, double centerY,
                                                         double sigmaX, double sigmaY,
                                                         double amplitude, double background) {
        BufferedImage noiseMap = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);

        // Convert the background value to a 0-255 range for the red component
        int backgroundRed = (int) (Math.min(background, 1.0) * 255);

        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                double gaussValue = GaussianFunction.compute2DGaussian(x, y, centerX, centerY,
                        sigmaX, sigmaY, amplitude);

                // Convert the Gaussian value (0-1 range) to a 0-255 range for the red component
                int redValue = (int) (Math.min(gaussValue, 1.0) * 255 + backgroundRed);
                redValue = Math.min(redValue, 255);  // Ensure the value doesn't exceed 255

                // Set the pixel color in the noise map
                Color color = new Color(redValue, 0, 0, 255);
                noiseMap.setRGB(x, y, color.getRGB());
            }
        }
        return noiseMap;
    }


}