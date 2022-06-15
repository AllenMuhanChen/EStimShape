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
import org.xper.alden.drawing.renderer.AbstractRenderer;
import org.xper.alden.drawing.renderer.PerspectiveRenderer;
import org.xper.allen.util.DPIUtil;
import org.xper.utils.RGBColor;

public class AllenPNGMaker{
	//int height = 224;
	//int width = 224;
	
	@Dependency 
	DPIUtil dpiUtil;
	@Dependency
	RGBColor backColor;
	@Dependency
	String generatorImageFolderName;
	@Dependency
	private
	String generatorNoiseMapFolderName;
	@Dependency
	double distance;
	@Dependency
	double pupilDistance;
	@Dependency
	double depth;
	AbstractRenderer pngRenderer;
	
	AllenDrawingManager window;
	int height = 1024;
	int width = 1024;
	
	public AllenPNGMaker(int width, int height) {
		this.width = width;
		this.height = height;
		
		pngRenderer = new PerspectiveRenderer();
		//renderer = new OrthographicRenderer();
		pngRenderer.setDepth(depth);
		pngRenderer.setDistance(distance); //TODO: stitch this into generator so it is a dependency
		pngRenderer.setPupilDistance(pupilDistance);
		pngRenderer.setHeight(height);
		pngRenderer.setWidth(width);
	}
	
	public AllenPNGMaker() {}

	/**
	 * 
	 */
	public void createDrawerWindow() {
		window = new AllenDrawingManager(height,width);
		window.setBackgroundColor(backColor.getRed(),backColor.getGreen(),backColor.getBlue());
		window.setPngMaker(this);
		window.init();
	}
	
	public void close() {
		window.close();
	}
	
	public String createAndSavePNGFromObj(AllenMatchStick obj, Long stimObjId, List<String> labels) {
		window.setImageFolderName(generatorImageFolderName);
		System.out.println("creating and saving PNG...");
		return window.drawStimulus(obj, stimObjId, labels);
	}
	/**
	 * Uses single window instance. 
	 * @param obj
	 * @param stimObjId
	 * @param labels
	 * @return
	 */
	public String createAndSaveNoiseMapFromObj(AllenMatchStick obj, Long stimObjId, List<String> labels) {
		window.setImageFolderName(generatorNoiseMapFolderName);
		System.out.println("creating and saving NoiseMap PNG...");
		return window.drawNoiseMap(obj, stimObjId,labels);
	}
	
	
	public List<String> createAndSavePNGsfromObjs(List<AllenMatchStick> objs,List<Long> stimObjIds, List<List<String>> labels) {
		AllenDrawingManager testWindow = new AllenDrawingManager(height,width);
		testWindow.setBackgroundColor(backColor.getRed(),backColor.getGreen(),backColor.getBlue());
		testWindow.setPngMaker(this);
		testWindow.setImageFolderName(generatorImageFolderName);
		System.out.println("creating and saving PNGs...");

		testWindow.setStimObjs(objs);
		testWindow.setStimObjIds(stimObjIds);
		
		List<String> paths = testWindow.drawStimuli(labels);				// draw object
		testWindow.close();
		System.out.println("...done saving PNGs");
		return paths;
	
	}
	
	public List<String> createAndSavePNGsfromObjs(List<AllenMatchStick> objs,List<Long> stimObjIds) {
		AllenDrawingManager testWindow = new AllenDrawingManager(height,width);
		testWindow.setBackgroundColor(backColor.getRed(),backColor.getGreen(),backColor.getBlue());
		testWindow.setPngMaker(this);
		testWindow.setImageFolderName(generatorImageFolderName);
		System.out.println("creating and saving PNGs...");

		testWindow.setStimObjs(objs);
		testWindow.setStimObjIds(stimObjIds);
		
		List<String> paths = testWindow.drawStimuli();				// draw object
		testWindow.close();
		System.out.println("...done saving PNGs");
		return paths;
	
	}
	public List<String> createAndSaveNoiseMapsfromObjs(List<AllenMatchStick> objs,List<Long> stimObjIds, List<List<String>> additionalLabels) {
		AllenDrawingManager testWindow = new AllenDrawingManager(height,width);
		testWindow.setBackgroundColor(1.0f, 0,0);
		testWindow.setPngMaker(this);
		testWindow.setImageFolderName(generatorNoiseMapFolderName);
		System.out.println("creating and Noise Map saving PNGs...");

		testWindow.setStimObjs(objs);
		testWindow.setStimObjIds(stimObjIds);
		
		int i=0;
		for(List<String> labels : additionalLabels) {
			List<String> newLabels = new ArrayList<>(labels);
			newLabels.add(0, "noisemap");
			additionalLabels.set(i,newLabels);
			i++;
		}
		
		List<String> paths = testWindow.drawNoiseMaps(additionalLabels);				// draw object
		testWindow.close();
		System.out.println("...done saving PNGs");
		return paths;
	}
	
	
	public void createAndSaveNoiseMapsfromObjs(List<AllenMatchStick> objs,List<Long> stimObjIds) {
		AllenDrawingManager testWindow = new AllenDrawingManager(height,width);
		testWindow.setBackgroundColor(1.0f, 0,0);
		testWindow.setPngMaker(this);
		testWindow.setImageFolderName(generatorNoiseMapFolderName);
		System.out.println("creating and Noise Map saving PNGs...");

		testWindow.setStimObjs(objs);
		testWindow.setStimObjIds(stimObjIds);
		
		LinkedList<String> labels = new LinkedList<>();
		labels.add("noisemap");
		testWindow.drawNoiseMaps();				// draw object
		testWindow.close();
		System.out.println("...done saving PNGs");
	}
	
	public String saveImage(long stimObjId, int height, int width,String imageFolderName) {
		byte[] data = screenShotBinary(width,height);  

		String path = imageFolderName + "/" + stimObjId + ".png";
		try {
			// new File(imageFolderName + "/" + stimObjId).mkdirs();
			
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
	
	public String saveImage(long stimObjId, List<String> labels, int height, int width,String imageFolderName) {
		byte[] data = screenShotBinary(width,height);  

		String path = imageFolderName + "/" + stimObjId;
		for (String str:labels) {
			path=path+"_"+str;
		}
		path=path+".png";
		
		try {
			// new File(imageFolderName + "/" + stimObjId).mkdirs();
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

	private byte[] screenShotBinaryRGB(int width, int height) 
	{
		System.out.println("Printing with legacy method");
		ByteBuffer framebytes = allocBytes(width * height * 3);

		int[] pixels = new int[width * height];
		int bindex;
		// grab a copy of the current frame contents as RGB (has to be UNSIGNED_BYTE or colors come out too dark)
		GL11.glReadPixels(0, 0, width, height, GL11.GL_RGB, GL11.GL_UNSIGNED_BYTE, framebytes);
		// copy RGB data from ByteBuffer to integer array
		for (int i = 0; i < pixels.length; i++) {
			bindex = i * 3;
			pixels[i] =
					0xFF000000                                          // A
					| ((framebytes.get(bindex)   & 0x000000FF) << 16)   // R
					| ((framebytes.get(bindex+1) & 0x000000FF) <<  8)   // G
					| ((framebytes.get(bindex+2) & 0x000000FF) <<  0);  // B
		}
		// free up this memory
		framebytes = null;
		// flip the pixels vertically (opengl has 0,0 at lower left, java is upper left)
		pixels = GLImage.flipPixels(pixels, width, height);

		try {
			ByteArrayOutputStream out = new ByteArrayOutputStream();
			BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
			image.setRGB(0, 0, width, height, pixels, 0, width);

			javax.imageio.ImageIO.write(image, "png", out);
			byte[] data = out.toByteArray();

			return data;
		}
		catch (Exception e) {
			System.out.println("screenShot(): exception " + e);
			return null;
		}
	}
	private byte[] screenShotBinary(int width, int height) 
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

		try {
			ByteArrayOutputStream out = new ByteArrayOutputStream();
			BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
			image.setRGB(0, 0, width, height, pixels, 0, width);

			javax.imageio.ImageIO.write(image, "png", out);
			byte[] data = out.toByteArray();

			return data;
		}
		catch (Exception e) {
			System.out.println("screenShot(): exception " + e);
			return null;
		}
	}

	public static ByteBuffer allocBytes(int howmany) {
		final int SIZE_BYTE = 4;
		return ByteBuffer.allocateDirect(howmany * SIZE_BYTE).order(ByteOrder.nativeOrder());
	}
	
	public void setBackColor(RGBColor backColor) {
		this.backColor = backColor;
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

	public AbstractRenderer getPngRenderer() {
		return pngRenderer;
	}

	public void setPngRenderer(AbstractRenderer pngRenderer) {
		this.pngRenderer = pngRenderer;
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

	public String getGeneratorImageFolderName() {
		return generatorImageFolderName;
	}

	public void setGeneratorImageFolderName(String generatorImageFolderName) {
		this.generatorImageFolderName = generatorImageFolderName;
	}

	public String getGeneratorNoiseMapFolderName() {
		return generatorNoiseMapFolderName;
	}

	public void setGeneratorNoiseMapFolderName(String generatorNoiseMapFolderName) {
		this.generatorNoiseMapFolderName = generatorNoiseMapFolderName;
	}
}
