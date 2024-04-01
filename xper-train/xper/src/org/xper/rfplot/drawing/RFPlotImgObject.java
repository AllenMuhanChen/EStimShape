package org.xper.rfplot.drawing;

import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;
import org.xper.rfplot.drawing.png.RecolorableImages;

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
    public void projectCoordinates(Coordinates2D mouseCoordinates) {
        // Vector direction from origin to mouse coordinates
        double dx = mouseCoordinates.getX();
        double dy = mouseCoordinates.getY();

        // Normalize this vector (make it unit length) to just get the direction
        double vectorLength = Math.sqrt(dx*dx + dy*dy);
        double dirX = dx / vectorLength;
        double dirY = dy / vectorLength;

        // Image (rectangle) dimensions
        double halfWidth = spec.getDimensions().getWidth() / 2.0;
        double halfHeight = spec.getDimensions().getHeight() / 2.0;

        // Project the rectangle's center to its edge in the direction of the vector
        // This is done by determining the 'projection factor' to reach the edge of the rectangle
        double projectionFactor = calculateProjectionFactor(dirX, dirY, halfWidth, halfHeight);

        // Update the mouseCoordinates to the edge of the rectangle in the vector direction
        mouseCoordinates.setX(dx + dirX * projectionFactor);
        mouseCoordinates.setY(dy + dirY * projectionFactor);
    }

    private double calculateProjectionFactor(double dirX, double dirY, double halfWidth, double halfHeight) {
        // The projection factor is the amount to scale the direction vector by
        // to reach the edge of the rectangle.
        // We calculate this separately for width and height to see which edge we hit first.

        // Avoid division by zero
        double factorX = dirX != 0 ? halfWidth / Math.abs(dirX) : Double.POSITIVE_INFINITY;
        double factorY = dirY != 0 ? halfHeight / Math.abs(dirY) : Double.POSITIVE_INFINITY;

        // The smaller factor determines the first edge hit by the projection.
        return Math.min(factorX, factorY);
    }
}