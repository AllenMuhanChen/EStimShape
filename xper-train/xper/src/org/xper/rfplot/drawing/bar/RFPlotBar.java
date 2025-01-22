package org.xper.rfplot.drawing.bar;

import com.thoughtworks.xstream.XStream;
import org.lwjgl.opengl.GL11;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.rfplot.XMLizable;
import org.xper.rfplot.drawing.DefaultSpecRFPlotDrawable;

import java.util.ArrayList;
import java.util.List;

public class RFPlotBar extends DefaultSpecRFPlotDrawable {
    public RFPlotBarSpec barSpec;

    public RFPlotBar() {
        setDefaultSpec();
    }

    @Override
    public void draw(Context context) {
        GL11.glPushMatrix();

        // Rotate
        GL11.glRotatef((float) barSpec.orientation, 0.0f, 0.0f, 1.0f);

        // Convert to mm
        float lengthMm = (float) context.getRenderer().deg2mm(barSpec.length);
        float widthMm = (float) context.getRenderer().deg2mm(barSpec.width);

        // Draw rectangle centered at origin
        GL11.glBegin(GL11.GL_QUADS);
        GL11.glVertex2f(-lengthMm/2, -widthMm/2);
        GL11.glVertex2f(lengthMm/2, -widthMm/2);
        GL11.glVertex2f(lengthMm/2, widthMm/2);
        GL11.glVertex2f(-lengthMm/2, widthMm/2);
        GL11.glEnd();

        GL11.glPopMatrix();
    }

    @Override
    public List<Coordinates2D> getOutlinePoints(AbstractRenderer renderer) {
        List<Coordinates2D> points = new ArrayList<>();
        float lengthMm = (float) renderer.deg2mm(barSpec.length);
        float widthMm = (float) renderer.deg2mm(barSpec.width);

        double cos = Math.cos(Math.toRadians(barSpec.orientation));
        double sin = Math.sin(Math.toRadians(barSpec.orientation));

        double[][] corners = {
                {-lengthMm/2, -widthMm/2},
                {lengthMm/2, -widthMm/2},
                {lengthMm/2, widthMm/2},
                {-lengthMm/2, widthMm/2}
        };

        for (double[] corner : corners) {
            double x = corner[0] * cos - corner[1] * sin;
            double y = corner[0] * sin + corner[1] * cos;
            points.add(new Coordinates2D(x, y));
        }

        return points;
    }

    @Override
    public void setSpec(String spec) {
        this.barSpec = RFPlotBarSpec.fromXml(spec);
    }

    @Override
    public String getSpec() {
        return barSpec.toXml();
    }

    @Override
    public void setDefaultSpec() {
        barSpec = new RFPlotBarSpec();
        barSpec.length = 5.0;
        barSpec.width = 1.0;
        barSpec.orientation = 0.0;
    }

    @Override
    public String getOutputData() {
        return String.format("length: %.2f, width: %.2f, orientation: %.1f",
                barSpec.length, barSpec.width, barSpec.orientation);
    }

    public static class RFPlotBarSpec implements XMLizable {
        public double length;
        public double width;
        public double orientation;

        static XStream s;
        static {
            s = new XStream();
            s.alias("BarSpec", RFPlotBarSpec.class);
        }

        public String toXml() {
            return s.toXML(this);
        }

        public static RFPlotBarSpec fromXml(String spec) {
            return (RFPlotBarSpec) s.fromXML(spec);
        }

        @Override
        public XMLizable getFromXml(String xml) {
            return fromXml(xml);
        }
    }
}