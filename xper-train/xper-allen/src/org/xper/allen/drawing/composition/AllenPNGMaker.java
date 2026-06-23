package org.xper.allen.drawing.composition;

import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.ArrayList;
import java.util.LinkedList;
import java.util.List;

import org.jzy3d.plot3d.rendering.image.GLImage;
import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.noisy.NAFCNoiseMapper;
import org.xper.allen.drawing.ga.Thumbnailable;
import org.xper.allen.util.DPIUtil;
import org.xper.utils.RGBColor;

public class AllenPNGMaker{
	@Dependency
	private DPIUtil dpiUtil;
	@Dependency
	private RGBColor backColor;
	@Dependency
	private double distance;
	@Dependency
	private double pupilDistance;
	@Dependency
	private double depth;
	@Dependency
	public int height;
	@Dependency
	public int width;
	@Dependency
    NAFCNoiseMapper noiseMapper;

	public AllenDrawingManager window = null;





	public AllenPNGMaker() {}

	public void createDrawerWindow() {
		if(window == null || !window.isOpen()) { //Only make a new window if there isn't one already
			window = new AllenDrawingManager(width, height, noiseMapper);
			window.setPngMaker(this);
			window.init();
		}

	}

	public String createAndSavePNG(Drawable obj, Long stimObjId, List<String> labels, String destinationFolder) {
		window.setImageFolderName(destinationFolder);
		window.setBackgroundColor(backColor.getRed(), backColor.getGreen(), backColor.getGreen());
		System.out.println("creating and saving PNG...");
		return window.drawStimulus(obj, stimObjId, labels);
	}

	public String createAndSaveThumbnail(Thumbnailable obj, Long stimObjId, List<String> labels, String destinationFolder) {
		window.setImageFolderName(destinationFolder);
		window.setBackgroundColor(backColor.getRed(), backColor.getGreen(), backColor.getGreen());
		System.out.println("creating and saving PNG...");
		return window.drawThumbnail(obj, stimObjId, labels);
	}

	/**
	 * Renders a match stick whose chosen components are drawn in {@code partTexture} and all
	 * other components in {@code baseTexture} (e.g. base SHADE with a few 2D limbs), then
	 * saves the composited result.
	 *
	 * <p>The shape is rendered three times from the identical pose — once all-{@code baseTexture},
	 * once all-{@code partTexture}, and once as a component-ID map — and combined per pixel by
	 * {@link LimbTextureCompositor}. See that class for why this is seamless and
	 * occlusion-correct.
	 *
	 * @param partComponents 1-indexed component numbers to draw in {@code partTexture}
	 */
	public String createAndSavePartTexturePNG(AllenMatchStick obj, Long stimObjId, List<String> labels,
											   String destinationFolder, String baseTexture, String partTexture,
											   java.util.Set<Integer> partComponents) {
		window.setImageFolderName(destinationFolder);
		window.setBackgroundColor(backColor.getRed(), backColor.getGreen(), backColor.getGreen());
		System.out.println("creating and saving part-texture PNG...");
		return window.drawPartTextureStimulus(obj, stimObjId, labels, baseTexture, partTexture, partComponents);
	}

	public String createAndSaveCompMap(AllenMatchStick obj, Long stimObjId, List<String> labels, String destinationFolder) {
		window.setImageFolderName(destinationFolder);
		window.setBackgroundColor(backColor.getRed(), backColor.getGreen(), backColor.getGreen());
		System.out.println("creating and saving PNG...");
		return window.drawCompMap(obj, stimObjId, labels);
	}

	public String createAndSaveCompMapThumbnail(Thumbnailable obj, Long stimObjId, List<String> labels, String destinationFolder) {
		window.setImageFolderName(destinationFolder);
		window.setBackgroundColor(backColor.getRed(), backColor.getGreen(), backColor.getGreen());
		System.out.println("creating and saving PNG...");
		return window.drawCompMapThumbnail(obj, stimObjId, labels);
	}

	public String createAndSavePNG(Drawable obj, Long stimObjId, String destinationFolder) {
		window.setImageFolderName(destinationFolder);
		window.setBackgroundColor(backColor.getRed(), backColor.getGreen(), backColor.getGreen());
		System.out.println("creating and saving PNG...");
		List<String> emptyLabels = new LinkedList<>();
		return window.drawStimulus(obj, stimObjId, emptyLabels);
	}

	public String createAndSaveCompGraphNoiseMap(AllenMatchStick obj, Long stimObjId, List<String> labels, String destinationFolder) {
		window.setImageFolderName(destinationFolder);
		window.setBackgroundColor(1.0f, 0.0f, 0.0f);
		System.out.println("creating and saving NoiseMap PNG...");
		return window.drawCompGraphNoiseMap(obj, stimObjId,labels);
	}

	public String createAndSaveNoiseMap(ProceduralMatchStick obj, Long stimObjId, List<String> labels, String destinationFolder, double amplitude, int specialCompIndx) {
		window.setImageFolderName(destinationFolder);
		window.setBackgroundColor(1.0f, 0.0f, 0.0f);
		System.out.println("creating and saving NoiseMap PNG...");
		try {
			return window.drawNoiseMap(obj, stimObjId,labels, amplitude, specialCompIndx);
		} catch (IOException e) {
			throw new RuntimeException(e);
		}
	}

	public String createAndSaveNoiseMap(ProceduralMatchStick obj, Long stimObjId, List<String> labels, String destinationFolder, double amplitude, List<Integer> specialCompIndcs) {
		window.setImageFolderName(destinationFolder);
		window.setBackgroundColor(1.0f, 0.0f, 0.0f);
		System.out.println("creating and saving NoiseMap PNG...");
		try {
			return window.drawNoiseMap(obj, stimObjId,labels, amplitude, specialCompIndcs);
		} catch (IOException e) {
			throw new RuntimeException(e);
		}
	}

	public void close() {
		window.close();
	}

	public List<String> createAndSaveBatchOfPNGs(List<AllenMatchStick> objs,List<Long> stimObjIds, List<List<String>> labels, String destinationFolder) {
		createDrawerWindow();

		int index=0;
		List<String> paths = new LinkedList<String>();
		for (AllenMatchStick obj:objs) {
			String path = createAndSavePNG(obj, stimObjIds.get(index), labels.get(index),destinationFolder);
			paths.add(path);
			index++;
		}

		window.close();
		System.out.println("...done saving PNGs");
		return paths;

	}

	public List<String> createAndSaveBatchOfPNGs(List<AllenMatchStick> objs,List<Long> stimObjIds, String destinationFolder) {


		return createAndSaveBatchOfPNGs(
				objs,
				stimObjIds,
				getEmptyLabels(objs.size()),
				destinationFolder
				);

	}

	private List<List<String>> getEmptyLabels(int numImagesToLabel){
		List<List<String>> emptyLabels = new ArrayList<List<String>>();
		for(int i=0; i<numImagesToLabel; i++) {
			ArrayList<String> labelsForOneImage = new ArrayList<String>();
			labelsForOneImage.add("");
			emptyLabels.add(labelsForOneImage);
		}

		return emptyLabels;

	}
	public List<String> createAndSaveBatchOfNoiseMaps(List<AllenMatchStick> objs,List<Long> stimObjIds, List<List<String>> additionalLabels, String destinationFolder) {
		createDrawerWindow();
		window.setImageFolderName(destinationFolder);
		System.out.println("creating and Noise Map saving PNGs...");
		List<String> paths = new LinkedList<String>();
		//		window.setStimObjs(objs);
		//		window.setStimObjIds(stimObjIds);

		appendNoisemapLabels(additionalLabels);

		int index=0;
		for(AllenMatchStick obj:objs) {
			String path = createAndSaveCompGraphNoiseMap(obj, stimObjIds.get(index), additionalLabels.get(index), destinationFolder);
			paths.add(path);
			index++;
		}

		window.close();
		System.out.println("...done saving PNGs");
		return paths;
	}

	private List<List<String>> appendNoisemapLabels(List<List<String>> additionalLabelsForNoiseMap) {
		int i=0;
		for(List<String> labelsForNoisemap : additionalLabelsForNoiseMap) {
			List<String> newLabelsForNoiseMap = new ArrayList<>(labelsForNoisemap);
			newLabelsForNoiseMap.add(0, "noisemap");
			additionalLabelsForNoiseMap.set(i,newLabelsForNoiseMap);
			i++;
		}
		return additionalLabelsForNoiseMap;
	}


	public List<String> createAndSaveBatchOfNoiseMaps(List<AllenMatchStick> objs,List<Long> stimObjIds, String destinationPath) {
		return createAndSaveBatchOfNoiseMaps(
				objs,
				stimObjIds,
				getEmptyLabels(objs.size()),
				destinationPath);
	}

	public String saveImage(long stimObjId, int height, int width,String imageFolderName) {
		List<String> labels = new LinkedList<String>();
		return saveImage(stimObjId, labels, height, width, imageFolderName);
	}

	public static String saveImage(long stimObjId, List<String> labels, int height, int width,String imageFolderName) {
		byte[] data = screenShotBinary(width,height);

		String path = imageFolderName + "/" + stimObjId;
		for (String str:labels) {
			if(!str.isEmpty())
				path=path+"_"+str;
		}
		path=path+".png";

		try {
			FileOutputStream fos = new FileOutputStream(path);
			fos.write(data);
			fos.close();
			return path;
		}

		catch (IOException e) {
			e.printStackTrace();
			return "Error: No Path";
		}
	}

	public static String saveImage(String filename, int height, int width, String imageFolderName) {
		byte[] data = screenShotBinary(width,height);

		String path = imageFolderName + "/" + filename;
		path=path+".png";

		try {
			FileOutputStream fos = new FileOutputStream(path);
			fos.write(data);
			fos.close();
			return path;
		}

		catch (IOException e) {
			e.printStackTrace();
			return "Error: No Path";
		}
	}

	/**
	 * Saves an already-built {@link BufferedImage} (e.g. a composite of several renders)
	 * using the same path/label convention as the frame-buffer {@code saveImage} methods.
	 */
	public static String saveImage(BufferedImage image, long stimObjId, List<String> labels, String imageFolderName) {
		String path = imageFolderName + "/" + stimObjId;
		for (String str:labels) {
			if(!str.isEmpty())
				path=path+"_"+str;
		}
		path=path+".png";

		try {
			javax.imageio.ImageIO.write(image, "png", new java.io.File(path));
			return path;
		}
		catch (IOException e) {
			e.printStackTrace();
			return "Error: No Path";
		}
	}

	public static byte[] screenShotBinary(int width, int height)
	{
		try {
			ByteArrayOutputStream out = new ByteArrayOutputStream();
			javax.imageio.ImageIO.write(captureFrame(width, height), "png", out);
			return out.toByteArray();
		}
		catch (Exception e) {
			System.out.println("screenShot(): exception " + e);
			return null;
		}
	}

	/**
	 * Reads the current OpenGL frame buffer into an ARGB {@link BufferedImage} (instead of
	 * encoding it straight to PNG bytes). Used when a frame needs further processing in
	 * memory, e.g. compositing several renders together before saving.
	 */
	public static BufferedImage captureFrame(int width, int height)
	{
		ByteBuffer framebytes = allocBytes(width * height * 3);

		int[] pixels = new int[width * height];
		int bindex;
		// grab a copy of the current frame contents as RGB (has to be UNSIGNED_BYTE or colors come out too dark)
		GL11.glReadPixels(0, 0, width, height, GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, framebytes);
		// copy RGB data from ByteBuffer to integer array
		for (int i = 0; i < pixels.length; i++) {
			bindex = i * 4;
			pixels[i] =
					((framebytes.get(bindex+3) & 0x000000FF) << 24)   // A                                 // A
					| ((framebytes.get(bindex)   & 0x000000FF) << 16)   // R
					| ((framebytes.get(bindex+1) & 0x000000FF) <<  8)   // G
					| ((framebytes.get(bindex+2) & 0x000000FF) <<  0);  // B
		}
		// free up this memory
		framebytes = null;
		// flip the pixels vertically (opengl has 0,0 at lower left, java is upper left)
		pixels = GLImage.flipPixels(pixels, width, height);

		BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
		image.setRGB(0, 0, width, height, pixels, 0, width);
		return image;
	}

	public static ByteBuffer allocBytes(int howmany) {
		final int SIZE_BYTE = 4;
		return ByteBuffer.allocateDirect(howmany * SIZE_BYTE).order(ByteOrder.nativeOrder());
	}

	public void setBackColor(RGBColor backColor) {
		this.backColor = backColor;
	}

	public void setBackColor(org.xper.drawing.RGBColor backColor) {
		this.backColor = new RGBColor(backColor.getRed(), backColor.getGreen(), backColor.getBlue());
	}

	public DPIUtil getDpiUtil() {
		return dpiUtil;
	}

	public void setDpiUtil(DPIUtil dpiUtil) {
		this.dpiUtil = dpiUtil;
	}

	public int getHeight() {
		return height;
	}

	public void setHeight(int height) {
		this.height = height;
	}

	public int getWidth() {
		return width;
	}

	public void setWidth(int width) {
		this.width = width;
	}

	public RGBColor getBackColor() {
		return backColor;
	}

	public double getDistance() {
		return distance;
	}

	public void setDistance(double distance) {
		this.distance = distance;
	}

	public double getPupilDistance() {
		return pupilDistance;
	}

	public void setPupilDistance(double pupilDistance) {
		this.pupilDistance = pupilDistance;
	}

	public double getDepth() {
		return depth;
	}

	public void setDepth(double depth) {
		this.depth = depth;
	}

	public NAFCNoiseMapper getNoiseMapper() {
		return noiseMapper;
	}

	public void setNoiseMapper(NAFCNoiseMapper noiseMapper) {
		this.noiseMapper = noiseMapper;
	}

	public AllenDrawingManager getWindow() {
		return window;
	}
}