package org.xper.allen.noisy;

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
import org.xper.png.ImageDimensions;
import org.xper.png.TranslatableResizableImages;
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

	private boolean drawNoise = true;


	public NoisyTranslatableResizableImages(int numNoiseFrames, int numImageTextures) {
		super(numNoiseFrames);
		this.numNoiseFrames = numNoiseFrames;
		this.numImageTextures = numImageTextures;
		this.currentNoiseIndx = numImageTextures;
		setTextureIds(BufferUtils.createIntBuffer(numNoiseFrames+numImageTextures+1));
	}

	/**
	 * Noise the whole png
	 * @param textureIndex
	 */
	public void loadNoise(int textureIndex) {
		for(int i=0; i<numNoiseFrames;i++) {
			byte[] noise = generateNoise(textureIndex);
			ByteBuffer pixels = (ByteBuffer)BufferUtils.createByteBuffer(noise.length).put(noise, 0x00000000, noise.length).flip();
			GL11.glEnable(GL11.GL_TEXTURE_2D);
			GL11.glBindTexture(GL11.GL_TEXTURE_2D, getTextureIds().get(numImageTextures+i));
			GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_NEAREST);
			GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_NEAREST);
			GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT, 4);
			GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0,  GL11.GL_RGBA8, getImgWidth().get(textureIndex), getImgHeight().get(textureIndex), 0,  GL11.GL_RGBA,  GL11.GL_BYTE, pixels);
		}
	}
	/**
	 * Load noise percentages from png. 
	 * @param pathname
	 * @param textureIndex
	 */
	public void loadNoise(String pathname, int textureIndex) {
		drawNoise = true;
//		System.out.println("AC4747823: noisepathname: " + pathname);
		try {
			File imageFile = new File(pathname);
			BufferedImage img = ImageIO.read(imageFile);
			byte[] src = ((DataBufferByte)img.getRaster().getDataBuffer()).getData();

			abgr2rgba(src);
			List<Double> noiseMap = new ArrayList<Double>(src.length/4);


			for(int i=0x00000000; i<src.length; i+=0x00000004) {
				double probability;
				int red;
				if(src[i]<0) {
					red = (int)src[i]+256;
					probability = (double)red/256.0;
				} else {
					red = (int)src[i];
					probability = (double) red/256.0;
				}
				noiseMap.add(probability);
			}



			for(int i=0; i<numNoiseFrames;i++) {
				byte[] noise = generateNoise(textureIndex, noiseMap);
				ByteBuffer pixels = (ByteBuffer)BufferUtils.createByteBuffer(noise.length).put(noise, 0x00000000, noise.length).flip();
//				GL11.glEnable(GL11.GL_TEXTURE_2D);
				GL11.glBindTexture(GL11.GL_TEXTURE_2D, getTextureIds().get(numImageTextures+i));
				GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_NEAREST);
				GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_NEAREST);
				GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT, 4);
				GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0,  GL11.GL_RGBA8, getImgWidth().get(textureIndex), getImgHeight().get(textureIndex), 0,  GL11.GL_RGBA,  GL11.GL_BYTE, pixels);
//				GL11.glDisable(GL11.GL_TEXTURE_2D);
			}

		}catch(Exception e) {
			System.out.println("No NoiseMap found. Will present stimulus without noise");
			drawNoise = false;
		}

	}

	private byte[] generateNoise(int textureIndex, List<Double> noiseMap) {
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
	 * @param noiseIndx
	 * @param context
	 * @param textureIndex
	 * @param location
	 * @param dimensions
	 */
	public void draw(int noiseIndx, Context context, int textureIndex, Coordinates2D location, ImageDimensions dimensions) {
		GL11.glPushMatrix();
		long textureStartTime = timeUtil.currentTimeMicros();
		drawTexture(context, textureIndex, location, dimensions);

		//			System.out.println("DRAW CALLED");
		if(drawNoise) {
			long noiseDrawStartTime = timeUtil.currentTimeMicros();
			drawNoise(noiseIndx, context, textureIndex, location, dimensions);
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

	private void drawNoise(int currentNoiseIndx, Context context, int textureIndex, Coordinates2D location, ImageDimensions dimensions) {
		//		GL11.glPushMatrix();
		GL11.glEnable(GL11.GL_TEXTURE_2D);  	
		//		System.out.println("AC:NOWREADING: " + (currentNoiseIndx+numImageTextures));
		GL11.glBindTexture(GL11.GL_TEXTURE_2D, getTextureIds().get(currentNoiseIndx+numImageTextures));
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
		//		currentNoiseIndx++;
//		System.out.println(currentNoiseIndx);
//		System.out.println(getTextureIds().capacity());
		//		GL11.glPopMatrix();
	}
	//	
	//	private void drawNoise(Context context, int textureIndex, Coordinates2D location, ImageDimensions dimensions) {
	//		
	////		GL11.glPushMatrix();
	//		GL11.glEnable(GL11.GL_TEXTURE_2D);  	
	//		GL11.glBindTexture(GL11.GL_TEXTURE_2D, getTextureIds().get(currentNoiseIndx));
	//		Coordinates2D centermm = new Coordinates2D(context.getRenderer().deg2mm(location.getX()), context.getRenderer().deg2mm(location.getY()));
	//
	//		float width = (float) context.getRenderer().deg2mm((float)dimensions.getWidth()); // texture.getImageWidth();
	//		float height = (float) context.getRenderer().deg2mm((float)dimensions.getHeight()); // texture.getImageHeight();		
	//
	//		float yOffset = -height / 2;	int imgWidth;
	//		int imgHeight;
	//		float xOffset = -width / 2; 
	//
	////		GL11.glTranslated(centermm.getX(), centermm.getY(), 0);
	//
	//		GL11.glColor3d(1.0, 1.0, 1.0);
	//		GL11.glBegin(GL11.GL_QUADS);
	//		GL11.glTexCoord2f(0, 1);
	//		GL11.glVertex2f(xOffset, yOffset);
	//		GL11.glTexCoord2f(1, 1);
	//		GL11.glVertex2f(xOffset + width, yOffset);
	//		GL11.glTexCoord2f(1, 0);
	//		GL11.glVertex2f(xOffset + width, yOffset + height);
	//		GL11.glTexCoord2f(0, 0);
	//		GL11.glVertex2f(xOffset, yOffset + height);
	//		GL11.glEnd();
	//		
	//		GL11.glDisable(GL11.GL_TEXTURE_2D);
	//		currentNoiseIndx++;
	//		System.out.println(currentNoiseIndx);
	//		System.out.println(getTextureIds().capacity());
	////		GL11.glPopMatrix();
	//	}

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

	public void cleanUpImage(){
		GL11.glDeleteTextures(getTextureIds());
		//		for(int i=0; i<getTextureIds().capacity(); i++) {
		//			GL11.glDeleteTextures(getTextureIds().get(i));
		//		}
		//textureIds.clear(); //Technically not needed since IntBuffer.get(int) does not step buffer?
	}

}
