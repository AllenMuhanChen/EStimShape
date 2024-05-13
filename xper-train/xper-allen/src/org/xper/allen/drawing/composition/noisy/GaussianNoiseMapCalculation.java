package org.xper.allen.drawing.composition.noisy;

import org.xper.alden.drawing.renderer.AbstractRenderer;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.drawing.Coordinates2D;

import javax.vecmath.Point2d;
import javax.vecmath.Point3d;
import javax.vecmath.Vector2d;
import javax.vecmath.Vector3d;
import java.awt.Color;
import java.awt.image.BufferedImage;

public class GaussianNoiseMapCalculation {

    public static BufferedImage generateGaussianNoiseMapFor(ProceduralMatchStick mStick,
                                                            int width, int height,
                                                            double sigmaDegrees,
                                                            double amplitude, double background,
                                                            AbstractRenderer renderer, int specialCompIndx){

        Point3d noiseOrigin = mStick.calculateNoiseOrigin(specialCompIndx);

        double sigmaPixels = degToPixels(renderer, sigmaDegrees);
        Coordinates2D noiseOriginPixels = convertToPixelCoordinates(noiseOrigin, renderer);

        return GaussianNoiseMapCalculation.generateTruncatedGaussianNoiseMap(width, height,
                noiseOriginPixels.getX(), noiseOriginPixels.getY(),
                degToPixels(renderer, ProceduralMatchStick.NOISE_RADIUS_DEGREES), amplitude,
                sigmaPixels, sigmaPixels,
                background);

    }

    private static double degToPixels(AbstractRenderer renderer, double degrees) {
        double mm = renderer.deg2mm(degrees);
        Coordinates2D pixels = renderer.mm2pixel(new Coordinates2D(mm, mm));
        return pixels.getX();

    }
    /**
     * Projects a 3D vector onto 2D by dropping the z-component.
     *
     * @param vector The 3D vector.
     * @return The 2D vector projection.
     */
    public static Vector2d projectTo2D(Vector3d vector) {
        return new Vector2d(vector.x, vector.y);
    }

    /**
     * Computes a point along the 2D tangent from a given 2D point.
     *
     * @param startPoint The starting 2D point.
     * @param tangent    The 2D tangent vector (not required to be normalized).
     * @param distance   The distance to move along the tangent.
     * @return A new 2D point along the tangent.
     */
    public static Point2d point2dAlongTangent(Point2d startPoint, Vector2d tangent, double distance) {
        // Normalize the tangent vector
        Vector2d normalizedTangent = new Vector2d(tangent);
        normalizedTangent.normalize();

        // Scale the tangent by the distance
        normalizedTangent.scale(distance);

        // Compute the new point
        return new Point2d(
                startPoint.x + normalizedTangent.x,
                startPoint.y + normalizedTangent.y
        );
    }

    private static Coordinates2D convertToPixelCoordinates(Point3d point3d, AbstractRenderer renderer) {
        double mm_x = renderer.deg2mm(point3d.x);
        double mm_y = renderer.deg2mm(point3d.y);
        Coordinates2D world_x_y = renderer.coord2pixel(new Coordinates2D(mm_x, mm_y));

        double scaledX = world_x_y.getX();
        double scaledY = world_x_y.getY();
        return new Coordinates2D(scaledX, scaledY);
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
        int backgroundRed;
        int noiseLevelRed;
        if (noiseLevel > background) {
            backgroundRed = (int) (Math.min(background, 1.0) * 255);
            noiseLevelRed = (int) (Math.min(noiseLevel, 1.0) * 255);
        } else{
            backgroundRed = 0;
            noiseLevelRed = (int) (Math.min(noiseLevel, 1.0) * 255);
        }

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