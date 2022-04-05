package org.xper.allen.noisy;

import java.awt.image.BufferedImage;
import java.awt.image.DataBufferByte;
import java.io.File;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.util.SplittableRandom;

import javax.imageio.ImageIO;

import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.GL11;
import org.xper.allen.drawing.png.ImageDimensions;
import org.xper.allen.drawing.png.TranslatableResizableImages;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.time.DefaultTimeUtil;
import org.xper.time.TimeUtil;

/**
 * Strategy for noise:
 * 1. LoadTexture should just load as pixels byte buffer. Process (i.e agbr2rgba, changing alpha). 
 * 2. Draw should
 * 	a. Generate noise pattern
 *  b. Draw saved pixels byte buffer
 *
 * 
 * @author Allen Chen
 *
 */
public class NoisyTranslatableResizableImages extends TranslatableResizableImages{
//	
	private int srcLength;
	private Context context;
	static SplittableRandom r = new SplittableRandom();
	TimeUtil timeUtil = new DefaultTimeUtil();
	public NoisyTranslatableResizableImages(int numNoiseFrames, int numImageTextures) {
		super(numNoiseFrames);
		setTextureIds(BufferUtils.createIntBuffer(numNoiseFrames+numImageTextures));
//		pixelsList = new ArrayList<>(numFrames);
		// TODO Auto-generated constructor stub
	}
	
	
	public void loadNoise(String pathname, int textureIndex) {
		
	}
	
	public void draw(boolean isNoised, Context context, int textureIndex, Coordinates2D location, ImageDimensions dimensions) {
		GL11.glPushMatrix();
		long textureStartTime = timeUtil.currentTimeMicros();
		drawTexture(context, textureIndex, location, dimensions);
		System.out.println("AC TIME TO DRAW TEXTURE: " + (timeUtil.currentTimeMicros() - textureStartTime));
		if(isNoised) {
//			System.out.println("DRAW CALLED");
			long noiseGenerateStartTime = timeUtil.currentTimeMicros();
			byte[] noise = generateNoise(textureIndex);
			System.out.println("AC TIME TO GEN NOISE: " + (timeUtil.currentTimeMicros()-noiseGenerateStartTime));
			long noiseDrawStartTime = timeUtil.currentTimeMicros();
			drawNoise(noise, context, textureIndex, location, dimensions);
			System.out.println("AC TIME TO DRAW NOISE: " + (timeUtil.currentTimeMicros()-noiseDrawStartTime));
		}
		GL11.glPopMatrix();
		
		
	}

	
	private void drawTexture(Context context, int textureIndex, Coordinates2D location, ImageDimensions dimensions) {
		
		Coordinates2D centermm = new Coordinates2D(context.getRenderer().deg2mm(location.getX()), context.getRenderer().deg2mm(location.getY()));
		//Coordinates2D centerPixels = context.getRenderer().mm2pixel(centermm);


		float width = (float) context.getRenderer().deg2mm((float)dimensions.getWidth()); // texture.getImageWidth();
		float height = (float) context.getRenderer().deg2mm((float)dimensions.getHeight()); // texture.getImageHeight();		

		float yOffset = -height / 2;	int imgWidth;
		int imgHeight;
		float xOffset = -width / 2; 
//		GL11.glPushMatrix();
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
		
		GL11.glDisable(GL11.GL_TEXTURE_2D);
//		GL11.glPopMatrix();
	}
	private void drawNoise(byte[] noise, Context context, int textureIndex, Coordinates2D location, ImageDimensions dimensions) {
		ByteBuffer pixels = (ByteBuffer)BufferUtils.createByteBuffer(noise.length).put(noise, 0x00000000, noise.length).flip();
//		GL11.glPushMatrix();
		GL11.glEnable(GL11.GL_TEXTURE_2D);
		GL11.glBindTexture(GL11.GL_TEXTURE_2D, NumFrames+1);
		GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_NEAREST);
		GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_NEAREST);
		GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT, 4);
		GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0,  GL11.GL_RGBA8, getImgWidth().get(textureIndex), getImgHeight().get(textureIndex), 0,  GL11.GL_RGBA,  GL11.GL_BYTE, pixels);
		
		Coordinates2D centermm = new Coordinates2D(context.getRenderer().deg2mm(location.getX()), context.getRenderer().deg2mm(location.getY()));

		float width = (float) context.getRenderer().deg2mm((float)dimensions.getWidth()); // texture.getImageWidth();
		float height = (float) context.getRenderer().deg2mm((float)dimensions.getHeight()); // texture.getImageHeight();		

		float yOffset = -height / 2;	int imgWidth;
		int imgHeight;
		float xOffset = -width / 2; 

//		GL11.glTranslated(centermm.getX(), centermm.getY(), 0);

		GL11.glColor3d(1.0, 1.0, 1.0);
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
		
		GL11.glDisable(GL11.GL_TEXTURE_2D);
//		GL11.glPopMatrix();
	}
	
	private byte[] generateNoise(int textureIndex) {
//		int width = getImgWidth().get(textureIndex);
//		int height = getImgHeight().get(textureIndex);
		byte pixels[] = new byte[srcLength];
		
		for(int i=0x00000000; i<pixels.length; i+=0x00000004) {
			if(r.nextDouble()<0.5) { //TODO: defer to map here.
				byte newByte = (byte) r.nextInt(265);
				
		
//				System.out.println("AC99484893: " + newByte[0]);
				pixels[i+0x00000000] = newByte;    //R
				pixels[i+0x00000001] = newByte;    //G
				pixels[i+0x00000002] = newByte;    //B
				pixels[i+0x00000003] = Byte.MAX_VALUE;//A
				
			}else { //set to all black, with zero alpha
				pixels[i+0x00000000] = Byte.MIN_VALUE; //R
				pixels[i+0x00000001] = Byte.MIN_VALUE; //G
				pixels[i+0x00000002] = Byte.MIN_VALUE; //B
				pixels[i+0x00000003] = Byte.MIN_VALUE; //A
			}
		}
		return pixels;
	}

	public int loadTexture(String pathname, int textureIndex) {
		try {
			File imageFile = new File(pathname);
			BufferedImage img = ImageIO.read(imageFile);
			getImgWidth().add(textureIndex, img.getWidth());
			getImgHeight().add(textureIndex, img.getHeight());
			//			System.out.println("loaded image : " + imgWidth + ", " + imgHeight);
			byte[] src = ((DataBufferByte)img.getRaster().getDataBuffer()).getData();
			this.srcLength = src.length;
			
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

}
