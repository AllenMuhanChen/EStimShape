package org.xper.rfplot.drawing.png;

import java.awt.image.BufferedImage;
import java.awt.image.DataBufferByte;
import java.io.File;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.IntBuffer;
import java.util.ArrayList;
import java.util.List;

import javax.imageio.ImageIO;

import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.GL11;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;

/**
 * Light version of JK's ImageStack with added functionality of changing location/size of each image on the stack.
 * Changes from ImageStack:
 *  - This class receives length units in degrees and converts them into mm for OpenGL
 * 	- Images are not loaded all at once inside of TranslatableResizableImages. They need to be loaded sequentially with loadTexture(),
 * 		stepping textureIndex each time.
 *  - initTextures() is ran before textures are loaded
 *  - numFrames is defined in the constructor
 *
 * @author Allen Chen
 *
 */
public class TranslatableResizableImages {
	private IntBuffer textureIds;
	protected int NumFrames;
	private List<Integer> imgWidth;
	private List<Integer> imgHeight;
	public TranslatableResizableImages(int numFrames) {
		this.NumFrames = numFrames;
		this.setTextureIds(BufferUtils.createIntBuffer(NumFrames));
		this.imgWidth = new ArrayList<>(numFrames);
		this.imgHeight = new ArrayList<>(numFrames);
	}

	/**
	 * Call this sometime before you load the textures. i.e in trialStart() in the Scene
	 */
	public void initTextures(){
		GL11.glGenTextures(getTextureIds());
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

		GL11.glColor3d(1.0, 1.0, 1.0);

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

//		GL11.glTexEnvi(GL11.GL_TEXTURE_ENV, GL11.GL_TEXTURE_ENV_MODE, GL11.GL_BLEND);

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
	 * Load's one image, with its index specified by textureIndex, and alpha specified (0-1). To load multiple images, call this method
	 * 	multiple times, incrementing textureIndex each time.
	 * @param pathname
	 * @param textureIndex
	 * @return
	 */
	public int loadTexture(String pathname, int textureIndex, double alpha) {
		try {
			File imageFile = new File(pathname);
			BufferedImage img = ImageIO.read(imageFile);
			getImgWidth().add(textureIndex, img.getWidth());
			getImgHeight().add(textureIndex, img.getWidth());
			//			System.out.println("loaded image : " + imgWidth + ", " + imgHeight);
			byte[] src = ((DataBufferByte)img.getRaster().getDataBuffer()).getData();

			//CHANGING ALPHA
			GL11.glEnable(GL11.GL_BLEND);
			GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);


			//bgr2rgb(src);
			abgr2rgba(src);

			byte byte_alpha = (byte) (alpha*255);
			changeAlpha(src, byte_alpha);

			//pixels = (ByteBuffer)BufferUtils.createByteBuffer(src.length).put(src, 0x00000000, src.length).flip();
			ByteBuffer pixels = (ByteBuffer)BufferUtils.createByteBuffer(src.length).put(src, 0x00000000, src.length).flip();


			GL11.glBindTexture(GL11.GL_TEXTURE_2D, getTextureIds().get(textureIndex));

			// from http://wiki.lwjgl.org/index.php?title=Multi-Texturing_with_GLSL
			GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_NEAREST);
			GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_NEAREST);
			GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT, 4);

			if(pixels.remaining() % 3 == 0) {
				// only for RGB
				GL11.glTexImage2D( GL11.GL_TEXTURE_2D, 0,  GL11.GL_RGBA8, img.getWidth(), img.getHeight(), 0,  GL11.GL_RGBA,  GL11.GL_UNSIGNED_BYTE, pixels);
				//GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0, GL11.GL_RGB, img.getWidth(), img.getHeight(), 0, GL11.GL_RGB, GL11.GL_UNSIGNED_BYTE, pixels);
			} else {
				// RGBA
				GL11.glTexImage2D( GL11.GL_TEXTURE_2D, 0,  GL11.GL_RGBA8, img.getWidth(), img.getHeight(), 0,  GL11.GL_RGBA,  GL11.GL_UNSIGNED_BYTE, pixels);
			}

			//System.out.println("JK 5353 ImageStack:loadTexture() " + imageFile + " : " + textureIndex +
			//	    				" textureIds = " + textureIds.get(textureIndex));

			return getTextureIds().get(textureIndex);

			//return 0;

		} catch(IOException e) {
			e.printStackTrace();
			System.err.println(pathname);
			throw new RuntimeException(e);
		}
	}


	public int loadTexture(String pathname, int textureIndex) {
		try {
			File imageFile = new File(pathname);
			BufferedImage img = ImageIO.read(imageFile);
			getImgWidth().add(textureIndex, img.getWidth());
			getImgHeight().add(textureIndex, img.getHeight());
			//			System.out.println("loaded image : " + imgWidth + ", " + imgHeight);
			byte[] src = ((DataBufferByte)img.getRaster().getDataBuffer()).getData();
//			System.out.println("AC0101010: " + Arrays.toString(src));
			//CHANGING ALPHA
			GL11.glEnable(GL11.GL_BLEND);
			GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);



			//
			//bgr2rgb(src);
			abgr2rgba(src);


			//pixels = (ByteBuffer)BufferUtils.createByteBuffer(src.length).put(src, 0x00000000, src.length).flip();
			ByteBuffer pixels = (ByteBuffer)BufferUtils.createByteBuffer(src.length).put(src, 0x00000000, src.length).flip();


			GL11.glBindTexture(GL11.GL_TEXTURE_2D, getTextureIds().get(textureIndex));

			// from http://wiki.lwjgl.org/index.php?title=Multi-Texturing_with_GLSL
			GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_NEAREST);
			GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_NEAREST);
			GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT, 4);

			if(pixels.remaining() % 3 == 0) {
				// only for RGB
				GL11.glTexImage2D( GL11.GL_TEXTURE_2D, 0,  GL11.GL_RGBA8, img.getWidth(), img.getHeight(), 0,  GL11.GL_RGBA,  GL11.GL_UNSIGNED_BYTE, pixels);
				//GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0, GL11.GL_RGB, img.getWidth(), img.getHeight(), 0, GL11.GL_RGB, GL11.GL_UNSIGNED_BYTE, pixels);
			} else {
				// RGBA
				GL11.glTexImage2D( GL11.GL_TEXTURE_2D, 0,  GL11.GL_RGBA8, img.getWidth(), img.getHeight(), 0,  GL11.GL_RGBA,  GL11.GL_UNSIGNED_BYTE, pixels);
			}

			//System.out.println("JK 5353 ImageStack:loadTexture() " + imageFile + " : " + textureIndex +
			//	    				" textureIds = " + textureIds.get(textureIndex));

			return getTextureIds().get(textureIndex);

			//return 0;

		} catch(IOException e) {
			e.printStackTrace();
			throw new RuntimeException(e);
		}
	}

	public void cleanUpImage(int textureIndex){
		GL11.glDeleteTextures(getTextureIds().get(textureIndex));
		//textureIds.clear(); //Technically not needed since IntBuffer.get(int) does not step buffer?
	}

	public void cleanUpTrial(){
		getTextureIds().clear();

	}

	protected void abgr2rgba(byte[] target) {
		byte tmpAlphaVal;
		byte tmpBlueVal;

		for(int i=0x00000000; i<target.length; i+=0x00000004) {
			tmpAlphaVal = target[i];
			target[i] = target[i+0x00000003];
			tmpBlueVal = target[i+0x00000001];
			target[i+0x00000001] = target[i+0x00000002];
			target[i+0x00000002] = tmpBlueVal;
			target[i+0x00000003] = tmpAlphaVal;

			/*
			target[i] = (byte) 0;
			target[i+0x00000001] = (byte) 255;
			target[i+0x00000002] = (byte) 255;
			target[i+0x00000003] = (byte) 255;
			*/
		}
	}

	protected void changeAlpha(byte[] target, byte alpha) {

		for(int i=0x00000000; i<target.length; i+=0x00000004) {
			double currentAlpha = target[i+0x00000003];
			double newAlpha = currentAlpha * (double) alpha;
//			System.out.println("AC12398032: " + newAlpha);
			byte alphaBytes = (byte) (newAlpha*255);
			target[i+0x00000003] = alphaBytes;

		}
	}

	private byte max(byte[] byteArray){
		byte max = byteArray[0];

		for (int i=1; i<byteArray.length; i++) {
			if (byteArray[i]>byteArray[i-1]){
				max = byteArray[i];
			}
		}
		return max;

	}

	private byte min(byte[] byteArray){
		byte min = byteArray[0];

		for (int i=1; i<byteArray.length; i++) {
			if (byteArray[i]<byteArray[i-1]){
				min = byteArray[i];
			}
		}
		return min;

	}

	protected IntBuffer getTextureIds() {
		return textureIds;
	}

	protected void setTextureIds(IntBuffer textureIds) {
		this.textureIds = textureIds;
	}

	protected List<Integer> getImgHeight() {
		return imgHeight;
	}

	protected void setImgHeight(List<Integer> imgHeight) {
		this.imgHeight = imgHeight;
	}

	protected List<Integer> getImgWidth() {
		return imgWidth;
	}

	protected void setImgWidth(List<Integer> imgWidth) {
		this.imgWidth = imgWidth;
	}

	protected void setImgWidth(int imgWidth) {
		this.imgWidth.add(imgWidth);
	}

	protected void setImgHeight(int imgHeight) {
		this.imgWidth.add(imgHeight);
	}



}