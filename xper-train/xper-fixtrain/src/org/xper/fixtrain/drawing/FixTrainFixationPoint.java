package org.xper.fixtrain.drawing;

import com.thoughtworks.xstream.XStream;
import org.lwjgl.opengl.GL11;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.drawing.renderer.AbstractRenderer;

public class FixTrainFixationPoint extends FixTrainDrawable<Double>{

    final FixationPointSpec fixationPointSpec = new FixationPointSpec();

    public FixTrainFixationPoint(double size, RGBColor color, boolean solid) {
        this.fixationPointSpec.setSize(size);
        this.fixationPointSpec.setColor(color);
        this.fixationPointSpec.setSolid(solid);
    }

    @Override
    public void draw(Context context) {
        AbstractRenderer renderer = context.getRenderer();
        double x = renderer.deg2mm(fixationPosition.getX());
        double y = renderer.deg2mm(fixationPosition.getY());
        Coordinates2D posInMm = new Coordinates2D(x,y);
        float width = (float) renderer.deg2mm(fixationPointSpec.getSize());
        float height = (float) renderer.deg2mm(fixationPointSpec.getSize());
        drawVertexes(posInMm, width, height);
    }

    private void drawVertexes(Coordinates2D posInMm, float width, float height) {
        double z = 0;

        float yOffset = -height / 2;
        float xOffset = -width / 2;

        GL11.glPushMatrix();
        GL11.glTranslated(posInMm.getX(), posInMm.getY(), z);
        GL11.glColor3f(fixationPointSpec.getColor().getRed(), fixationPointSpec.getColor().getGreen(), fixationPointSpec.getColor().getBlue());

        if (fixationPointSpec.isSolid()) {
            GL11.glBegin(GL11.GL_QUADS);
        } else {
            GL11.glBegin(GL11.GL_LINE_LOOP);
        }
        GL11.glVertex3d(xOffset, yOffset, z);
        GL11.glVertex3d(xOffset + width, yOffset, z);
        GL11.glVertex3d(xOffset + width, yOffset + height, z);
        GL11.glVertex3d(xOffset, yOffset+height, z);
        GL11.glEnd();
        GL11.glPopMatrix();
    }

    static{
        XStream s = new XStream();
        s.alias("FixTrainFixationPoint", FixTrainFixationPoint.class);
    }


    @Override
    public void setSpec(String spec) {
        FixationPointSpec p = FixationPointSpec.fromXml(spec);
        this.fixationPointSpec.setSize(p.getSize());
        this.fixationPointSpec.setColor(p.getColor());
        this.fixationPointSpec.setSolid(p.isSolid());
    }

    @Override
    public void nextDrawable() {
        //do nothing, we want to keep the same fixation point
    }

    @Override
    public void scaleSize(double scale) {
        this.fixationPointSpec.setSize(fixationPointSpec.getSize() * scale);
    }

    @Override
    public Double getSize() {
        return fixationPointSpec.getSize();
    }

    @Override
    public String getSpec() {
        return fixationPointSpec.toXml();
    }
}