package org.xper.allen.drawing.composition.noisy;

import org.xper.alden.drawing.renderer.AbstractRenderer;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.stick.JuncPt_struct;
import javax.vecmath.Point2d;
import javax.imageio.ImageIO;
import javax.vecmath.Point2d;
import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.List;

import javax.vecmath.Point2d;
import javax.vecmath.Vector3d;

import static org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper.convertMmToPixelCoordinates;
import static org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper.mmToPixels;

public class LineNoiseMapper implements NoiseMapper{
    private int width;
    private int height;
    private double background;

    @Override
    public String mapNoise(ProceduralMatchStick mStick,
                           double amplitude,
                           int specialCompIndx,
                           AbstractRenderer renderer,
                           String path) {
        File outputFile = new File(path);
        BufferedImage img = generateLineNoiseMapFor(mStick, width, height, amplitude, background, renderer, specialCompIndx);
        try {
            ImageIO.write(img, "png", outputFile);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        return outputFile.getAbsolutePath();
    }

    @Override
    public String mapNoise(ProceduralMatchStick mStick, double amplitude, List<Integer> specialCompIndx, AbstractRenderer renderer, String path) {
        return null;
    }

    public static BufferedImage generateLineNoiseMapFor(ProceduralMatchStick mStick,
                                                        int width, int height,
                                                        double amplitude, double background,
                                                        AbstractRenderer renderer, int specialCompIndx) {
        mStick.noiseRadiusMm = 0;
        Point3d noiseOrigin = mStick.calculateNoiseOrigin(specialCompIndx);
        Vector3d projectedTangent = mStick.projectedTangent;

        // Calculate the perpendicular vector in the X,Y plane
        Vector3d perpendicularVector = new Vector3d(-projectedTangent.y, projectedTangent.x, 0);
        perpendicularVector.normalize();

        Coordinates2D noiseOriginPixels = convertMmToPixelCoordinates(noiseOrigin, renderer);

        Point3d specialPoint = mStick.getComp()[specialCompIndx].getMassCenter();
        Coordinates2D specialPointPixels = convertMmToPixelCoordinates(specialPoint, renderer);

        // Determine if specialPoint is above or below the line
        double distance = (specialPointPixels.getX() - noiseOriginPixels.getX()) * perpendicularVector.x +
                (specialPointPixels.getY() - noiseOriginPixels.getY()) * perpendicularVector.y;

        boolean aboveLine = distance < 0;

        return generateLineNoiseMap(width, height, perpendicularVector,
                new Point2d(noiseOriginPixels.getX(), noiseOriginPixels.getY()),
                amplitude, background, aboveLine);
    }

    public static BufferedImage generateLineNoiseMap(int width, int height,
                                                     Vector3d lineDirection, Point2d interceptPoint,
                                                     double noiseLevel, double background,
                                                     boolean aboveLine) {
        BufferedImage noiseMap = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);

        // Convert the background and noiseLevel values to a 0-255 range for the red component
        int backgroundRed = (int) (Math.min(background, 1.0) * 255);
        int noiseLevelRed = (int) (Math.min(noiseLevel, 1.0) * 255);

        // Calculate 2D angle from Vector3d
        double angleRad = Math.atan2(lineDirection.y, lineDirection.x);
        double cosAngle = Math.cos(angleRad);
        double sinAngle = Math.sin(angleRad);

        // Calculate the line's normal vector
        double normalX = -sinAngle;
        double normalY = cosAngle;

        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                // Calculate the signed distance from the point to the line
                double distance = (x - interceptPoint.x) * normalX + (y - interceptPoint.y) * normalY;

                // Determine if this point is on the specified side of the line
                boolean isOnSpecifiedSide = (aboveLine && distance > 0) || (!aboveLine && distance < 0);

                int redValue = isOnSpecifiedSide ? noiseLevelRed : backgroundRed;

                // Set the pixel color in the noise map
                Color color = new Color(redValue, 0, 0, 255);
                noiseMap.setRGB(x, y, color.getRGB());
            }
        }
        return noiseMap;
    }

    public int getWidth() {
        return width;
    }

    public void setWidth(int width) {
        this.width = width;
    }

    public int getHeight() {
        return height;
    }

    public void setHeight(int height) {
        this.height = height;
    }

    public double getBackground() {
        return background;
    }

    public void setBackground(double background) {
        this.background = background;
    }
}