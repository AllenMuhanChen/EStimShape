package org.xper.allen.drawing.mstickbubbles;

import org.xper.allen.drawing.bubbles.NoisyPixel;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.drawing.Coordinates2D;

import javax.imageio.ImageIO;
import javax.vecmath.Point3d;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.List;

public class MStickBubble {
    AllenMatchStick matchStick;
    String imgPath;

    public List<NoisyPixel> generateBubblePixels() throws IOException {
        BufferedImage image = ImageIO.read(new File(imgPath));

        Point3d[] points = matchStick.getComp()[1].getmAxisInfo().getmPts();
        return null;
    }
}