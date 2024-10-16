package org.xper.rfplot.drawing;

import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;
import org.xper.rfplot.drawing.png.RecolorableImages;

import java.util.ArrayList;
import java.util.List;

public class RFPlotImgObject extends DefaultSpecRFPlotDrawable{

    private PngSpec spec;
    private RecolorableImages images;

    private String defaultPath;

    public RFPlotImgObject(String defaultPath) {
        this.defaultPath = defaultPath;
        setDefaultSpec();
    }

    @Override
    public void draw(Context context) {
        images.initTextures();
        images.loadTexture(spec.getPath(), 0);
        images.draw(context, 0, new Coordinates2D(spec.getxCenter(), spec.getyCenter()), spec.getDimensions());
    }

    @Override
    public void setSpec(String spec) {
        this.spec = PngSpec.fromXml(spec);
    }

    @Override
    public void setDefaultSpec() {
        spec = new PngSpec();
        spec.setPath(defaultPath);
        spec.setAlpha(1);
        spec.setDimensions(new ImageDimensions(10,10));
        spec.setxCenter(0);
        spec.setyCenter(0);

        images = new RecolorableImages(1);
    }

    @Override
    public String getSpec() {
        return spec.toXml();
    }

    @Override
    public List<Coordinates2D> getOutlinePoints(AbstractRenderer renderer) {
        //in the GUI because these don't change the spec, only the xfm spec.
        int numberOfPoints = 100;
        List<Coordinates2D> profilePoints = new ArrayList<>();

        // Image (rectangle) dimensions
        double width = renderer.deg2mm(spec.getDimensions().getWidth());
        double height = renderer.deg2mm(spec.getDimensions().getHeight());

        // Calculate the total perimeter of the rectangle
        double perimeter = 2 * (width + height);

        // Length of each segment along the perimeter, based on the number of points
        double segmentLength = perimeter / numberOfPoints;

        for (int i = 0; i < numberOfPoints; i++) {
            // Calculate the distance along the perimeter for the current point
            double currentDistance = i * segmentLength;

            // Determine the position of the current point based on currentDistance
            double x = 0, y = 0;
            if (currentDistance <= width) {
                // Top edge
                x = currentDistance;
                y = 0;
            } else if (currentDistance <= width + height) {
                // Right edge
                x = width;
                y = currentDistance - width;
            } else if (currentDistance <= 2 * width + height) {
                // Bottom edge
                x = width - (currentDistance - (width + height));
                y = height;
            } else {
                // Left edge
                x = 0;
                y = height - (currentDistance - (2 * width + height));
            }

            // Adjust coordinates to be centered at 0,0
            x += 0 - width / 2;
            y += 0 - height / 2;

            // Add the new point to the list of profile points
            profilePoints.add(new Coordinates2D(x, y));
        }

        return profilePoints;
    }

    @Override
    public String getOutputData() {
        return spec.toXml();
    }
}