package org.xper.allen.drawing.composition.noisy;

import org.xper.alden.drawing.renderer.AbstractRenderer;
import org.xper.allen.drawing.composition.AllenMAxisArc;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.AllenTubeComp;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.stick.JuncPt_struct;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;
import java.awt.Color;
import java.awt.image.BufferedImage;
import java.util.Arrays;
import java.util.List;

public class GaussianNoiseMapCalculation {

    public static final double NOISE_RADIUS_DEGREES = 5;

    public static BufferedImage generateGaussianNoiseMapFor(AllenMatchStick mStick,
                                                            int width, int height,
                                                            double sigmaX, double sigmaY,
                                                            double amplitude, double background,
                                                            AbstractRenderer renderer){
        List<Integer> specialEnds = mStick.getSpecialEndComp();
        for (Integer specialCompIndx: specialEnds){
            AllenTubeComp specialComp = mStick.getComp()[specialCompIndx];
            AllenMAxisArc specialArc = specialComp.getmAxisInfo();
            Point3d point3d = new Point3d();

            for (JuncPt_struct junc: mStick.getJuncPt()){
                if (junc != null) {
                    int numMatch = Arrays.stream(junc.getComp()).filter(x -> x == specialCompIndx).toArray().length;
                    if (numMatch == 1) {
                        int junctionCompIndex = -1;
                        int[] connectedComps = junc.getComp();
                        for (int comp:connectedComps){
                            if (comp==specialCompIndx && comp!=0){
                                junctionCompIndex = comp;
                            }
                        }
                        Vector3d tangent = junc.getTangent()[junctionCompIndex];
                        tangent.negate();
                        point3d = pointAlongTangent(junc.getPos(), tangent, NOISE_RADIUS_DEGREES);
                    }
                }
            }


//            Point3d point3d = specialArc.getmPts()[26];

            Coordinates2D scaled = convertToPixelCoordinates(point3d, renderer);

            return GaussianNoiseMapCalculation.generateTruncatedGaussianNoiseMap(width, height,
                    scaled.getX(), scaled.getY(),
                    degToPixels(renderer, NOISE_RADIUS_DEGREES), amplitude,
                    sigmaX, sigmaY,
                    background);
        }
        return null;
    }

    private static double degToPixels(AbstractRenderer renderer, double degrees) {
        double mm = renderer.deg2mm(degrees);
        Coordinates2D pixels = renderer.mm2pixel(new Coordinates2D(mm, mm));
        return pixels.getX();

    }

    /**
     * Computes a point along the tangent from a given point.
     *
     * @param startPoint The starting point.
     * @param tangent    The tangent vector (not required to be normalized).
     * @param distance   The distance to move along the tangent.
     * @return A new point along the tangent.
     */
    public static Point3d pointAlongTangent(Point3d startPoint, Vector3d tangent, double distance) {
        // Normalize the tangent vector
        Vector3d normalizedTangent = new Vector3d(tangent);
        normalizedTangent.normalize();

        // Scale the tangent by the distance
        normalizedTangent.scale(distance);

        // Compute the new point
        Point3d newPoint = new Point3d(
                startPoint.x + normalizedTangent.x,
                startPoint.y + normalizedTangent.y,
                startPoint.z + normalizedTangent.z
        );

        return newPoint;
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