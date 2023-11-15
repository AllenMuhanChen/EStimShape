package org.xper.allen.noisy;

import java.awt.*;
import java.awt.image.BufferedImage;
import java.awt.image.DataBufferByte;
import java.io.File;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

import javax.imageio.IIOException;
import javax.imageio.ImageIO;

import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.GL11;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.TranslatableResizableImages;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.time.DefaultTimeUtil;
import org.xper.time.TimeUtil;

/**
 * Loads a noiseMap as a png, where the red value of each pixel represents
 * the percentage chance a corresponding pixel should be random noise.
 *
 * Intended usage is to pre-generate all of the noise before stimulus presentation.
 * Storage of the noise is handled within OpenGL's BindTexture feature.
 *
 * noiseIndx (which noise tex is drawn) is specified as a arguement to draw()
 * This is to give more control over when exactly noise is stepped
 * (for the ability to slow down noise if for some reason is wanted)
 *
 * One can easily make a new draw() method that steps through currentNoiseIndx
 * automatically if they wish.
 *
 *
 * @author Allen Chen
 *
 */
public class NoisyTranslatableResizableImages extends TranslatableResizableImages{
	public boolean showTiming = false;
	//
	private int numNoiseFrames;
	private int numImageTextures;
	private int srcLength;
	private Context context;
	static SplittableRandom r = new SplittableRandom();
	private int currentNoiseIndx;
	TimeUtil timeUtil = new DefaultTimeUtil();

	private final static double RANGE = Byte.MAX_VALUE - Byte.MIN_VALUE;


	public NoisyTranslatableResizableImages(int numNoiseFrames, int numImageTextures) {
		super(numNoiseFrames);
		this.numNoiseFrames = numNoiseFrames;
		this.numImageTextures = numImageTextures;
		this.currentNoiseIndx = 0;
		setTextureIds(BufferUtils.createIntBuffer(numNoiseFrames+numImageTextures+1));
	}

	/**
	 * Load noise percentages from png.
	 * @param pathname
	 * @param color
	 */
	public void loadNoise(String pathname, Color color) {
				System.out.println("AC4747823: noisepathname: " + pathname);
		try {
			File imageFile = new File(pathname);
			BufferedImage img = ImageIO.read(imageFile);

			int width = img.getWidth();
			int height = img.getHeight();

			byte[] src = ((DataBufferByte)img.getRaster().getDataBuffer()).getData();

			abgr2rgba(src);
			List<Double> noiseMap = new ArrayList<Double>(src.length/4);


			for(int i=0x00000000; i<src.length; i+=0x00000004) {
				double probability;
				int red;
				if(src[i]<0) {
					red = (int)src[i]+256;
				} else {
					red = src[i];
				}
				probability = (double)red/255.0;
				noiseMap.add(probability);
			}



			byte[] noise = new byte[srcLength];
//			color = new Color(1.0f, 0.0f, 0.0f);
			for(int i=0; i<numNoiseFrames;i++) {
				if (i==0){
					noise = generateNoise(noiseMap, color);
				} else{
					noise = generateTwinkleNoise(0.5, noise, color);

				}
				ByteBuffer pixels = (ByteBuffer)BufferUtils.createByteBuffer(noise.length).put(noise, 0x00000000, noise.length).flip();
				GL11.glBindTexture(GL11.GL_TEXTURE_2D, getTextureIds().get(numImageTextures+i));
				GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_NEAREST);
				GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_NEAREST);
				GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT, 4);
				GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0,  GL11.GL_RGBA8, width, height, 0,  GL11.GL_RGBA,  GL11.GL_UNSIGNED_BYTE, pixels);
			}

		}catch(Exception e) {
			System.out.println("No NoiseMap found. Will present stimulus without noise");
		}

	}

	private byte[] generateTwinkleNoise(double twinkleChance, byte[] previousNoise, Color baseColor){
		byte newPixels[] = new byte[srcLength];
		// Convert baseColor to HSL/HSV values
		float[] hsl = Color.RGBtoHSB(baseColor.getRed(), baseColor.getGreen(), baseColor.getBlue(), null);
		for(int i=0x00000000; i<newPixels.length; i+=0x00000004) {
			if (previousNoise[i + 0x00000003] == -1) { //-1 is MAX unsigned byte value
				if (r.nextDouble() < twinkleChance) {
					// Random lightness value
					calculateNoisePixels(newPixels,hsl,i);  // A (255 in terms of unsigned byte, full opacity)
				} else {
					newPixels[i + 0x00000000] = previousNoise[i + 0x00000000];    //R
					newPixels[i + 0x00000001] = previousNoise[i + 0x00000001];    //G
					newPixels[i + 0x00000002] = previousNoise[i + 0x00000002];    //B
					newPixels[i + 0x00000003] = previousNoise[i + 0x00000003]; //A
				}
			}
		}
		return newPixels;
	}

	private byte[] generateNoise(List<Double> noiseMap, Color baseColor) {
		byte pixels[] = new byte[srcLength];

		// Convert baseColor to HSL/HSV values
		float[] hsl = Color.RGBtoHSB(baseColor.getRed(), baseColor.getGreen(), baseColor.getBlue(), null);

		for(int i = 0; i < pixels.length; i += 4) {
			if (r.nextDouble() < noiseMap.get(i / 4)) {
				calculateNoisePixels(pixels, hsl, i);
			} else {
				// Set to all black, with zero alpha. 0 is smallest unsigned byte value
				pixels[i] = 0;     // R
				pixels[i + 1] = 0; // G
				pixels[i + 2] = 0; // B
				pixels[i + 3] = 0; // A
			}
		}
		return pixels;
	}

	private void calculateNoisePixels(byte[] pixels, float[] hsl, int i) {
// Original lightness value
		float originalLightness = hsl[2];
		float newLightness;
		if (originalLightness < 1) {
			// Calculate the maximum fluctuation range based on the current lightness
			float fluctuationRange = Math.min(originalLightness, 1.0f - originalLightness);

			// Generate a random fluctuation within the allowed range
			float fluctuation = (float) ((r.nextDouble() * fluctuationRange * 2) - fluctuationRange);

			// Apply the fluctuation to the original lightness, ensuring the result is within [0,1]
			newLightness = originalLightness + fluctuation;
			newLightness = Math.max(0.0f, Math.min(1.0f, newLightness)); // Clamp to [0,1]
		} else {
			// If the original lightness is already at the maximum, don't change it
			newLightness = (float) r.nextDouble();
		}

		// Create a Color object from the HSL values with the new lightness
		Color color = Color.getHSBColor(hsl[0], hsl[1], newLightness);
		// Get the RGB components from the Color object
		int intRed = color.getRed();
		int intGreen = color.getGreen();
		int intBlue = color.getBlue();

		// Cast the integer values to byte values
		byte red = (byte) intRed;
		byte green = (byte) intGreen;
		byte blue = (byte) intBlue;

		// Set the pixel to the new RGB color with max alpha
		pixels[i] = red;    // R
		pixels[i + 1] = green;  // G
		pixels[i + 2] = blue;   // B
		pixels[i + 3] =  -1;  // Alpha (set to max value for opacity)
	}



	private byte[] generateNoise(List<Double> noiseMap) {
		//		int width = getImgWidth().get(textureIndex);
		//		int height = getImgHeight().get(textureIndex);
		byte pixels[] = new byte[srcLength];

		for(int i=0x00000000; i<pixels.length; i+=0x00000004) {
			if(r.nextDouble()<noiseMap.get((int) Math.floor(i/4))) { //TODO: defer to map here.
				byte newByte = (byte) r.nextInt(256);


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

	/**
	 * Draw from pre-loaded noise textures.
	 * @param context
	 * @param textureIndex
	 * @param location
	 * @param dimensions
	 */
	public void draw(boolean drawNoise, Context context, int textureIndex, Coordinates2D location, ImageDimensions dimensions) {
		GL11.glPushMatrix();
		long textureStartTime = timeUtil.currentTimeMicros();
		drawTexture(context, textureIndex, location, dimensions);

		//			System.out.println("DRAW CALLED");
		if(drawNoise) {
			long noiseDrawStartTime = timeUtil.currentTimeMicros();
			drawNoise(context, location, dimensions);
			if(showTiming)
				System.out.println("AC TIME TO DRAW NOISE: " + (timeUtil.currentTimeMicros()-noiseDrawStartTime));
		}
		GL11.glPopMatrix();
	}

	//	//Not preload drawing. Depricated
	//	public void draw(Context context, int textureIndex, Coordinates2D location, ImageDimensions dimensions) {
	//		GL11.glPushMatrix();
	//		long textureStartTime = timeUtil.currentTimeMicros();
	//		drawTexture(context, textureIndex, location, dimensions);
	//		System.out.println("AC TIME TO DRAW TEXTURE: " + (timeUtil.currentTimeMicros() - textureStartTime));
	//		GL11.glPopMatrix();
	//	}


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

	private void drawNoise(Context context, Coordinates2D location, ImageDimensions dimensions) {
		GL11.glEnable(GL11.GL_TEXTURE_2D);
		GL11.glBindTexture(GL11.GL_TEXTURE_2D, getTextureIds().get(currentNoiseIndx+numImageTextures));
		Coordinates2D centermm = new Coordinates2D(context.getRenderer().deg2mm(location.getX()), context.getRenderer().deg2mm(location.getY()));

		float width = (float) context.getRenderer().deg2mm((float)dimensions.getWidth()); // texture.getImageWidth();
		float height = (float) context.getRenderer().deg2mm((float)dimensions.getHeight()); // texture.getImageHeight();

		float yOffset = -height / 2;	int imgWidth;
		int imgHeight;
		float xOffset = -width / 2;

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

		currentNoiseIndx++;
	}

	public int loadTexture(String pathname, int textureIndex) {
		try {
			File imageFile = new File(pathname);
			BufferedImage img = null;
			try {
				img = ImageIO.read(imageFile);
			} catch(IIOException e){
				System.err.println("Could not read image: " + imageFile.getAbsolutePath().toString());
			}
			getImgWidth().add(textureIndex, img.getWidth());
			getImgHeight().add(textureIndex, img.getHeight());
			//			System.out.println("loaded image : " + imgWidth + ", " + imgHeight);
			byte[] src = ((DataBufferByte)img.getRaster().getDataBuffer()).getData();
			this.srcLength = src.length;

			//			System.out.println("AC0101010: " + Arrays.toString(src));
			//CHANGING ALPHA
//			GL11.glEnable(GL11.GL_BLEND);
//			GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);



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

	public void cleanUpImage(){
		GL11.glDeleteTextures(getTextureIds());
		//		for(int i=0; i<getTextureIds().capacity(); i++) {
		//			GL11.glDeleteTextures(getTextureIds().get(i));
		//		}
		//textureIds.clear(); //Technically not needed since IntBuffer.get(int) does not step buffer?
	}

}