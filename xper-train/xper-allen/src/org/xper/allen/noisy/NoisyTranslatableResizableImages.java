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
 * @author Allen Chen
 *
 */
public class NoisyTranslatableResizableImages extends TranslatableResizableImages {
	public boolean showTiming = false;
	//
	private int numNoiseFrames;
	private int numImageTextures;
	private double noiseRate;
	private int srcLength;
	private Context context;
	static SplittableRandom r = new SplittableRandom();
	private int currentNoiseIndx;
	private int currentFrameIndx = 0;
	TimeUtil timeUtil = new DefaultTimeUtil();

	private final static double RANGE = Byte.MAX_VALUE - Byte.MIN_VALUE;
	private double[][][] pinkNoise3D;

	public NoisyTranslatableResizableImages(int numNoiseFrames, int numImageTextures, double noiseRate) {
		super(numNoiseFrames);
		this.numNoiseFrames = numNoiseFrames;
		this.numImageTextures = numImageTextures;
		this.noiseRate = noiseRate;
		this.currentNoiseIndx = 0;
		setTextureIds(BufferUtils.createIntBuffer(numNoiseFrames + numImageTextures + 1));
	}

	public void loadNoise(String pathname, Color color) {
		String noiseType = "twinkle";
		System.out.println("AC4747823: noisepathname: " + pathname);
		try {
			File imageFile = new File(pathname);
			BufferedImage img = ImageIO.read(imageFile);

			int width = img.getWidth();
			int height = img.getHeight();

			byte[] src = ((DataBufferByte) img.getRaster().getDataBuffer()).getData();

			abgr2rgba(src);
			List<Double> noiseMap = new ArrayList<Double>(src.length / 4);

			for (int i = 0; i < src.length; i += 4) {
				double probability;
				int red;
				if (src[i] < 0) {
					red = (int) src[i] + 256;
				} else {
					red = src[i];
				}
				probability = (double) red / 255.0;
				noiseMap.add(probability);
			}

			if ("pink".equalsIgnoreCase(noiseType)) {
				generatePinkNoise3D(width, height, numNoiseFrames);
				for (int i = 0; i < numNoiseFrames; i++) {
					byte[] noise = generatePinkNoise(noiseMap, color, i);
					createNoiseFrameTexture(noise, i, width, height);
				}
			} else if ("twinkle".equalsIgnoreCase(noiseType)) {
				byte[] noise = new byte[srcLength];
				for (int i = 0; i < numNoiseFrames; i++) {
					if (i == 0) {
						noise = generateNoise(noiseMap, color);
					} else {
						noise = generateTwinkleNoise(0.5, noise, color);
					}
					createNoiseFrameTexture(noise, i, width, height);
				}
			} else {
				for (int i = 0; i < numNoiseFrames; i++) {
					byte[] noise = generateNoise(noiseMap, color);
					createNoiseFrameTexture(noise, i, width, height);
				}
			}
		} catch (Exception e) {
			System.out.println("No NoiseMap found. Will present stimulus without noise");
		}
	}

	private void createNoiseFrameTexture(byte[] noise, int frameNumber, int width, int height) {
		ByteBuffer pixels = (ByteBuffer) BufferUtils.createByteBuffer(noise.length).put(noise, 0, noise.length).flip();
		GL11.glBindTexture(GL11.GL_TEXTURE_2D, getTextureIds().get(numImageTextures + frameNumber));
		GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_NEAREST);
		GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_NEAREST);
		GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT, 4);
		GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0, GL11.GL_RGBA8, width, height, 0, GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, pixels);
	}

	private byte[] generateTwinkleNoise(double twinkleChance, byte[] previousNoise, Color baseColor) {
		byte newPixels[] = new byte[srcLength];
		// Convert baseColor to HSL/HSV values
		float[] hsl = Color.RGBtoHSB(baseColor.getRed(), baseColor.getGreen(), baseColor.getBlue(), null);
		for (int i = 0; i < newPixels.length; i += 4) {
			if (previousNoise[i + 3] == -1) { // -1 is MAX unsigned byte value
				if (r.nextDouble() < twinkleChance) {
					// Random lightness value
					calculateNoisePixels(newPixels, hsl, i);  // A (255 in terms of unsigned byte, full opacity)
				} else {
					newPixels[i] = previousNoise[i];    // R
					newPixels[i + 1] = previousNoise[i + 1];    // G
					newPixels[i + 2] = previousNoise[i + 2];    // B
					newPixels[i + 3] = previousNoise[i + 3]; // A
				}
			}
		}
		return newPixels;
	}

	private byte[] generateNoise(List<Double> noiseMap, Color baseColor) {
		byte pixels[] = new byte[srcLength];

		// Convert baseColor to HSL/HSV values
		float[] hsl = Color.RGBtoHSB(baseColor.getRed(), baseColor.getGreen(), baseColor.getBlue(), null);

		for (int i = 0; i < pixels.length; i += 4) {
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

	private void generatePinkNoise3D(int width, int height, int depth) {
		pinkNoise3D = new double[width][height][depth];
		double[] state = new double[16];
		for (int z = 0; z < depth; z++) {
			for (int y = 0; y < height; y++) {
				for (int x = 0; x < width; x++) {
					double white = r.nextDouble() * 2 - 1;
					state[0] = 0.99886 * state[0] + white * 0.0555179;
					state[1] = 0.99332 * state[1] + white * 0.0750759;
					state[2] = 0.96900 * state[2] + white * 0.1538520;
					state[3] = 0.86650 * state[3] + white * 0.3104856;
					state[4] = 0.55000 * state[4] + white * 0.5329522;
					state[5] = -0.7616 * state[5] - white * 0.0168980;
					pinkNoise3D[x][y][z] = state[0] + state[1] + state[2] + state[3] + state[4] + state[5] + white * 0.5362;
					state[5] = white;
				}
			}
		}
	}

	private byte[] generatePinkNoise(List<Double> noiseMap, Color baseColor, int frame) {
		int width = pinkNoise3D.length;
		int height = pinkNoise3D[0].length;
		byte pixels[] = new byte[width * height * 4];

		// Convert baseColor to HSL/HSV values
		float[] hsl = Color.RGBtoHSB(baseColor.getRed(), baseColor.getGreen(), baseColor.getBlue(), null);

		for (int y = 0; y < height; y++) {
			for (int x = 0; x < width; x++) {
				int index = (y * width + x) * 4;
				if (r.nextDouble() < noiseMap.get(y * width + x)) {
					// Adjust the lightness based on the pink noise value
					float noiseLightness = (float) (hsl[2] * (1.0 + pinkNoise3D[x][y][frame]));

					// Clamp the lightness value between 0 and 1
					noiseLightness = Math.max(0.0f, Math.min(1.0f, noiseLightness));

					// Create a new color with the adjusted lightness
					Color noiseColor = Color.getHSBColor(hsl[0], hsl[1], noiseLightness);

					// Set the pixel to the new RGB color with max alpha
					pixels[index] = (byte) noiseColor.getRed();    // R
					pixels[index + 1] = (byte) noiseColor.getGreen();  // G
					pixels[index + 2] = (byte) noiseColor.getBlue();   // B
					pixels[index + 3] = -1;  // Alpha (set to max value for opacity)
				} else {
					// Set to all black, with zero alpha. 0 is smallest unsigned byte value
					pixels[index] = 0;     // R
					pixels[index + 1] = 0; // G
					pixels[index + 2] = 0; // B
					pixels[index + 3] = 0; // A
				}
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
		pixels[i + 3] = -1;  // Alpha (set to max value for opacity)
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

		if (drawNoise) {
			// only draw noise based on noiseRate.
			// 1 means play noise on every frame
			// 0.5 means play noise on every other frame
			drawNoise(context, location, dimensions);
			if (noiseRate != 0) {
				if (currentFrameIndx % (int) Math.ceil(1 / noiseRate) == 0) {
					currentNoiseIndx++;
				}
			} else {
				currentNoiseIndx = 0;
			}
		}
		currentFrameIndx++;
		GL11.glPopMatrix();
	}

	private void drawTexture(Context context, int textureIndex, Coordinates2D location, ImageDimensions dimensions) {
		Coordinates2D centermm = new Coordinates2D(context.getRenderer().deg2mm(location.getX()), context.getRenderer().deg2mm(location.getY()));

		float width = (float) context.getRenderer().deg2mm((float) dimensions.getWidth());
		float height = (float) context.getRenderer().deg2mm((float) dimensions.getHeight());

		float yOffset = -height / 2;
		float xOffset = -width / 2;

		GL11.glTranslated(centermm.getX(), centermm.getY(), 0);
		GL11.glColor3d(1.0, 1.0, 1.0);

		GL11.glEnable(GL11.GL_TEXTURE_2D);
		GL11.glBindTexture(GL11.GL_TEXTURE_2D, getTextureIds().get(textureIndex));

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
	}

	private void drawNoise(Context context, Coordinates2D location, ImageDimensions dimensions) {
		GL11.glEnable(GL11.GL_TEXTURE_2D);
		GL11.glBindTexture(GL11.GL_TEXTURE_2D, getTextureIds().get(currentNoiseIndx + numImageTextures));
		Coordinates2D centermm = new Coordinates2D(context.getRenderer().deg2mm(location.getX()), context.getRenderer().deg2mm(location.getY()));

		float width = (float) context.getRenderer().deg2mm((float) dimensions.getWidth());
		float height = (float) context.getRenderer().deg2mm((float) dimensions.getHeight());

		float yOffset = -height / 2;
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
	}

	public int loadTexture(String pathname, int textureIndex) {
		try {
			File imageFile = new File(pathname);
			BufferedImage img = null;
			try {
				img = ImageIO.read(imageFile);
			} catch (IIOException e) {
				System.err.println("Could not read image: " + imageFile.getAbsolutePath().toString());
			}
			getImgWidth().add(textureIndex, img.getWidth());
			getImgHeight().add(textureIndex, img.getHeight());
			byte[] src = ((DataBufferByte) img.getRaster().getDataBuffer()).getData();
			this.srcLength = src.length;

			GL11.glEnable(GL11.GL_BLEND);
			GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);

			abgr2rgba(src);

			ByteBuffer pixels = (ByteBuffer) BufferUtils.createByteBuffer(src.length).put(src, 0, src.length).flip();

			GL11.glBindTexture(GL11.GL_TEXTURE_2D, getTextureIds().get(textureIndex));

			GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_NEAREST);
			GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_NEAREST);
			GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT, 4);

			if (pixels.remaining() % 3 == 0) {
				GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0, GL11.GL_RGBA8, img.getWidth(), img.getHeight(), 0, GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, pixels);
			} else {
				GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0, GL11.GL_RGBA8, img.getWidth(), img.getHeight(), 0, GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, pixels);
			}

			return getTextureIds().get(textureIndex);

		} catch (IOException e) {
			e.printStackTrace();
			throw new RuntimeException(e);
		}
	}

	public void cleanUpImage() {
		GL11.glDeleteTextures(getTextureIds());
	}
}