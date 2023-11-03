package org.xper.alden.drawing.drawables;

import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.List;

import org.jzy3d.plot3d.rendering.image.GLImage;
import org.lwjgl.opengl.GL11;
import org.xper.drawing.stick.MatchStick;
import org.xper.utils.RGBColor;

public class PNGmaker {
	//int height = 224;
	//int width = 224;
	int height = 1024;
	int width = 1024;
	RGBColor backColor = new RGBColor(0,0,0);
	
	public PNGmaker(int width, int height) {
		this.width = width;
		this.height = height;
	}
	
	public PNGmaker() {}

	public void createAndSavePNGsfromObjs(List<MatchStick> objs,List<Long> stimObjIds,String imageFolderName) {
		DrawingManager testWindow = new DrawingManager(height,width);
		testWindow.setBackgroundColor(backColor.getRed(),backColor.getGreen(),backColor.getBlue());
		testWindow.setPngMaker(this);
		testWindow.setImageFolderName(imageFolderName);
		System.out.println("creating and saving PNGs...");

		testWindow.setStimObjs(objs);
		testWindow.setStimObjIds(stimObjIds);
		
		testWindow.drawStimuli();				// draw object
		testWindow.close();
		System.out.println("...done saving PNGs");
	}
	
	public void saveImage(long stimObjId, int height, int width,String imageFolderName) {
		byte[] data = screenShotBinary(width,height);  

		try {
			// new File(imageFolderName + "/" + stimObjId).mkdirs();
			FileOutputStream fos = new FileOutputStream(imageFolderName + "/" + stimObjId + ".png");
		    fos.write(data);
		    fos.close();
		} 
		catch (IOException e) {
			e.printStackTrace();
		}
	}

	private byte[] screenShotBinary(int width, int height) 
	{
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

	public static ByteBuffer allocBytes(int howmany) {
		final int SIZE_BYTE = 4;
		return ByteBuffer.allocateDirect(howmany * SIZE_BYTE).order(ByteOrder.nativeOrder());
	}
	
	public void setBackColor(RGBColor backColor) {
		this.backColor = backColor;
	}
}