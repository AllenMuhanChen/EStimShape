package org.xper.allen.drawing.png;

import java.awt.image.BufferedImage;
import java.awt.image.DataBufferByte;
import java.io.File;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.IntBuffer;

import javax.imageio.ImageIO;

import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.GL11;
import org.lwjgl.util.glu.GLU;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;

/**
 * Light version of JK's ImageStack with added functionality of changing location of each image on the stack.
 * Changes from ImageStack:
 * 	- Images are not loaded all at once inside of TranslatableImages. They need to be loaded sequentially with loadTexture(), 
 * 		stepping textureIndex each time.
 *  - initTextures() is ran before textures are loaded 
 *  - numFrames is defined in the constructor
 * 
 * @author Allen Chen
 *
 */
public class TranslatableImages {
	IntBuffer textureIds; 
	int NumFrames;
	int imgWidth;
	int imgHeight;
	public TranslatableImages(int numFrames) {
		this.NumFrames = numFrames;
		this.textureIds = BufferUtils.createIntBuffer(NumFrames);
	}

	/**
	 * Call this sometime before you load the textures. i.e in trialStart() in the Scene
	 */
	public void initTextures(){
		GL11.glGenTextures(textureIds); 
	}
	
	public void draw(Context context, int textureIndex, Coordinates2D location) {

		Coordinates2D centermm = new Coordinates2D(context.getRenderer().deg2mm(location.getX()), context.getRenderer().deg2mm(location.getY()));
		Coordinates2D centerPixels = context.getRenderer().mm2pixel(centermm);
		
		float width = imgWidth; // texture.getImageWidth();
		float height = imgHeight; // texture.getImageHeight();		

		float yOffset = -height / 2;	int imgWidth;
		int imgHeight;
		float xOffset = -width / 2; 
		

		GL11.glPushMatrix();
		GL11.glTranslated(centerPixels.getX(), centerPixels.getY(), 0);
		
		GL11.glColor3d(1.0, 1.0, 1.0);
		
		GL11.glEnable(GL11.GL_TEXTURE_2D);  	
		GL11.glBindTexture(GL11.GL_TEXTURE_2D, textureIds.get(textureIndex));
		/*	
		// from http://wiki.lwjgl.org/index.php?title=Multi-Texturing_with_GLSL
		GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_NEAREST);
		GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_NEAREST);
		GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0, GL11.GL_RGB, imgWidth, imgHeight, 0, GL11.GL_RGB, GL11.GL_UNSIGNED_BYTE, pixels);
		GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT, 4);
		 */	
		

		
		
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
	/**
	 * Load's one image, with its index specified by textureIndex. To load multiple images, call this method
	 * 	multiple times, incrementing textureIndex each time. 
	 * @param pathname
	 * @param textureIndex
	 * @return
	 */
	public int loadTexture(String pathname, int textureIndex) {
		try {
			File imageFile = new File(pathname);
			BufferedImage img = ImageIO.read(imageFile);
			imgWidth = img.getWidth();
			imgHeight = img.getHeight();
//			System.out.println("loaded image : " + imgWidth + ", " + imgHeight);
			byte[] src = ((DataBufferByte)img.getRaster().getDataBuffer()).getData();
	
//			
			//bgr2rgb(src);
			abgr2rgba(src);
			
			//pixels = (ByteBuffer)BufferUtils.createByteBuffer(src.length).put(src, 0x00000000, src.length).flip();
			ByteBuffer pixels = (ByteBuffer)BufferUtils.createByteBuffer(src.length).put(src, 0x00000000, src.length).flip();
			
			GL11.glBindTexture(GL11.GL_TEXTURE_2D, textureIds.get(textureIndex));

    		// from http://wiki.lwjgl.org/index.php?title=Multi-Texturing_with_GLSL
    		GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_NEAREST);
    		GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_NEAREST);
    		GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT, 4);

    		if(pixels.remaining() % 3 == 0) {
    			// only for RGB
    		 	GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0, GL11.GL_RGB, img.getWidth(), img.getHeight(), 0, GL11.GL_RGB, GL11.GL_UNSIGNED_BYTE, pixels);
    		} else {
    			// RGBA
    			GL11.glTexImage2D( GL11.GL_TEXTURE_2D, 0,  GL11.GL_RGBA8, img.getWidth(), img.getHeight(), 0,  GL11.GL_RGBA,  GL11.GL_UNSIGNED_BYTE, pixels);
    		}
    		   
    		//System.out.println("JK 5353 ImageStack:loadTexture() " + imageFile + " : " + textureIndex + 
    		//	    				" textureIds = " + textureIds.get(textureIndex));    		

    		return textureIds.get(textureIndex);
			
			//return 0; 
	
		} catch(IOException e) {
			e.printStackTrace();
			throw new RuntimeException(e);
		}
	}
	
	public void cleanUpImage(int textureIndex){
		GL11.glDeleteTextures(textureIds.get(textureIndex));
		//textureIds.clear(); //Technically not needed since IntBuffer.get(int) does not step buffer?
	}
	
	public void cleanUpTrial(){
		textureIds.clear();

	}
	
    void abgr2rgba(byte[] target) {
    	byte tmpAlphaVal;
    	byte tmpBlueVal;
    	
    	for(int i=0x00000000; i<target.length; i+=0x00000004) {
    		tmpAlphaVal = target[i];
    		target[i] = target[i+0x00000003];
    		tmpBlueVal = target[i+0x00000001];
    		target[i+0x00000001] = target[i+0x00000002];
    		target[i+0x00000002] = tmpBlueVal;
    		target[i+0x00000003] = tmpAlphaVal;
    	}
    }

}
