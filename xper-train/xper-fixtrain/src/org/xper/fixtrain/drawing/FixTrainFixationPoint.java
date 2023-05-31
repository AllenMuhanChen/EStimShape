package org.xper.fixtrain.drawing;

import com.thoughtworks.xstream.XStream;
import org.lwjgl.opengl.GL11;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.drawing.renderer.AbstractRenderer;

public class FixTrainFixationPoint extends FixTrainDrawable{

    double size;
    RGBColor color;
    boolean solid = true;

    public FixTrainFixationPoint(double size, RGBColor color, boolean solid) {
        this.size = size;
        this.color = color;
        this.solid = solid;
        this.fixationPosition = new Coordinates2D(0,0);
    }

    @Override
    public void draw(Context context) {
        AbstractRenderer renderer = context.getRenderer();
        double x = renderer.deg2mm(fixationPosition.getX());
        double y = renderer.deg2mm(fixationPosition.getY());
        Coordinates2D posInMm = new Coordinates2D(x,y);
        drawVertexes(posInMm);
    }

    private void drawVertexes(Coordinates2D posInMm) {
        double z = 0;

        GL11.glColor4f(color.getRed(), color.getGreen(), color.getBlue(), 1f);

        GL11.glPushMatrix();
        GL11.glTranslated(posInMm.getX(), posInMm.getY(), z);
        if (solid) {
            GL11.glBegin(GL11.GL_QUADS);
        } else {
            GL11.glBegin(GL11.GL_LINE_LOOP);
        }
        GL11.glVertex3d(-size/2., -size/2., z);
        GL11.glVertex3d(size/2., -size/2., z);
        GL11.glVertex3d(size/2., size/2., z);
        GL11.glVertex3d(-size/2., size/2., z);
        GL11.glEnd();
        GL11.glPopMatrix();
    }

    static{
        XStream s = new XStream();
        s.alias("FixTrainFixationPoint", FixTrainFixationPoint.class);
    }

    public FixTrainFixationPoint() {
    }

    public static FixTrainFixationPoint fromXml(String xml) {
        XStream s = new XStream();
        return (FixTrainFixationPoint)s.fromXML(xml);
    }

    public String toXml() {
        XStream s = new XStream();
        return s.toXML(this);
    }

    @Override
    public void setSpec(String spec) {
        FixTrainFixationPoint p = fromXml(spec);
        this.fixationPosition = p.fixationPosition;
        this.size = p.size;
        this.color = p.color;
        this.solid = p.solid;
    }

    @Override
    public String getSpec() {
        return toXml();
    }
}