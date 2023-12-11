package org.xper.rfplot.drawing.png;

import org.lwjgl.opengl.GL11;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

public class RecolorableImages extends TranslatableResizableImages{
    public RecolorableImages(int numFrames) {
        super(numFrames);
    }

    public void draw(Context context, int textureIndex, Coordinates2D location, ImageDimensions dimensions) {
        Coordinates2D centermm = new Coordinates2D(context.getRenderer().deg2mm(location.getX()), context.getRenderer().deg2mm(location.getY()));
        //Coordinates2D centerPixels = context.getRenderer().mm2pixel(centermm);


        float width = (float) context.getRenderer().deg2mm((float)dimensions.getWidth()); // texture.getImageWidth();
        float height = (float) context.getRenderer().deg2mm((float)dimensions.getHeight()); // texture.getImageHeight();

        float yOffset = -height / 2;	int imgWidth;
        int imgHeight;
        float xOffset = -width / 2;


        GL11.glPushMatrix();
        GL11.glTranslated(centermm.getX(), centermm.getY(), 0);



        GL11.glEnable(GL11.GL_TEXTURE_2D);
        GL11.glBindTexture(GL11.GL_TEXTURE_2D, getTextureIds().get(textureIndex));
		/*
		// from http://wiki.lwjgl.org/index.php?title=Multi-Texturing_with_GLSL
		GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_NEAREST);
		GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_NEAREST);
		GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0, GL11.GL_RGB, imgWidth, imgHeight, 0, GL11.GL_RGB, GL11.GL_UNSIGNED_BYTE, pixels);
		GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT, 4);
		 */
//

//		GL11.glTexEnvi(GL11.GL_TEXTURE_ENV, GL11.GL_TEXTURE_ENV_MODE, GL11.GL_MULT);

        GL11.glBegin(GL11.GL_QUADS);
        GL11.glTexCoord2f(0, 1);
        GL11.glVertex2f(xOffset, yOffset);
        GL11.glTexCoord2f(1, 1);
        GL11.glVertex2f(xOffset + width, yOffset);
        GL11.glTexCoord2f(1, 0);
        GL11.glVertex2f(xOffset + width, yOffset + height);
        GL11.glTexCoord2f(0, 0);
        GL11.glVertex2f(xOffset, yOffset + height);
        GL11.glEnd();


        GL11.glPopMatrix();

        //CLEANUP

        //
        GL11.glDisable(GL11.GL_TEXTURE_2D);
    }
}