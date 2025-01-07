package org.xper.allen.drawing.mstickbubbles;

import org.xper.alden.drawing.renderer.AbstractRenderer;
import org.xper.allen.drawing.bubbles.NoisyPixel;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.drawing.Coordinates2D;

import javax.imageio.ImageIO;
import javax.vecmath.Point3d;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.List;

public class MStickBubbleGenerator {
    int width = 1000;
    int height = 1000;
    AbstractRenderer renderer;

    public BufferedImage generateBubbleMap(AllenMatchStick matchStick) throws IOException {
        BufferedImage bubbleMap = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
        Point3d[] points = matchStick.getComp()[1].getmAxisInfo().getmPts();
        Point3d[] correctedPoints = new Point3d[points.length];

        Point3d massCenter = matchStick.getMassCenter();
        for (int i = 0; i < points.length; i++) {
            Point3d correctedPoint = new Point3d(points[i]);
            correctedPoint.sub(massCenter);
            correctedPoint.scale(matchStick.getScaleForMAxisShape());
            correctedPoint.add(massCenter);
            correctedPoints[i] = correctedPoint;
        }

        for (int i = 1; i < correctedPoints.length; i++) {
            Point3d point = correctedPoints[i];
            Coordinates2D xy = mmToPixels(renderer, new Coordinates2D(point.x, point.y));

            // Pack ARGB values manually
            int argb = (255 << 24) |    // Alpha = 255 (fully opaque)
                    (255 << 16) |    // Red = 255
                    (0 << 8)    |    // Green = 0
                    0;              // Blue = 0

            bubbleMap.setRGB((int) xy.getX(), (int) xy.getY(), argb);
        }
        return bubbleMap;
    }

    public static Coordinates2D mmToPixels(AbstractRenderer renderer, Coordinates2D mm) {
        return renderer.coord2pixel(mm);
    }
    public static double mmToPixels(AbstractRenderer renderer, double mm) {
        Coordinates2D pixels = renderer.mm2pixel(new Coordinates2D(mm, mm));
        return pixels.getX();

    }
}