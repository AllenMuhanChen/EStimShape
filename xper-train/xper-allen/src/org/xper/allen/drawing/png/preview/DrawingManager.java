package org.xper.allen.drawing.png.preview;

import java.util.ArrayList;
import java.util.List;

import org.lwjgl.opengl.Display;
import org.lwjgl.opengl.DisplayMode;
import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.PixelFormat;
import org.xper.drawing.Context;
import org.xper.drawing.Drawable;
import org.xper.drawing.RGBColor;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveRenderer;

public class DrawingManager implements Drawable{
	Drawable stimObj;
	
	List<? extends Drawable> stimObjs = new ArrayList<Drawable>();
	List<Long> stimObjIds = new ArrayList<Long>();
	
	int nStim = 0;
	int stimCounter = 0;
	RGBColor backgroundColor = new RGBColor(0.5f,0.5f,0.5f); 
	
	String imageFolderName = "";
	
	int height;
	int width;
	
	PNGmaker pngMaker;
	
	BaseWindow window;
	AbstractRenderer renderer;
	
	public DrawingManager() {
		super();
		DisplayMode mode = Display.getDisplayMode();
		width = mode.getWidth() / 2;
		height = mode.getHeight() / 2;
	}
	
	public DrawingManager(int height, int width) {
		super();
		this.height = height;
		this.width = width;
	}
	
	public void drawStimuli() {
		window = new BaseWindow(height,width);
		
		PixelFormat pixelFormat = new PixelFormat(0, 8, 1, 4);
		window.setPixelFormat(pixelFormat);
		window.create();
		
		renderer = new PerspectiveRenderer();
		renderer.setDepth(6000);
		renderer.setDistance(635);
		renderer.setPupilDistance(50);
		renderer.setHeight(height);
		renderer.setWidth(width);
		renderer.init(window.getWidth(), window.getHeight());
		
		GL11.glShadeModel(GL11.GL_SMOOTH);
		GL11.glDisable(GL11.GL_DEPTH_TEST);
		
		GL11.glClearColor(backgroundColor.getRed(),backgroundColor.getGreen(),backgroundColor.getGreen(),1);
		
		Context context = new Context();
		
		while(stimCounter < nStim) {
			GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT | GL11.GL_STENCIL_BUFFER_BIT);
			GL11.glClearColor(backgroundColor.getRed(),backgroundColor.getGreen(),backgroundColor.getGreen(),1);
			renderer.draw(this,context);
			window.swapBuffers();
			
//			if (!imageFolderName.isEmpty())
//				pngMaker.saveImage_file(stimObjIds.get(stimCounter),height,width, imageFolderName);
//			pngMaker.saveImage_db(stimObjIds.get(stimCounter),height,width);
			try {
				Thread.sleep(1000);
			} catch (InterruptedException e) {
				e.printStackTrace();
			}
			stimCounter++;
		}
		window.destroy();
	}

	public void draw(Context context) {
		GL11.glClearColor(backgroundColor.getRed(),backgroundColor.getGreen(),backgroundColor.getGreen(),1);
				
		if (nStim > 0) {
			stimObjs.get(stimCounter).draw(context);
		}
	}
	
	public void setBackgroundColor(float r_bkgrd,float g_bkgrd,float b_bkgrd) {
		this.backgroundColor.setRed(r_bkgrd);
		this.backgroundColor.setGreen(g_bkgrd);
		this.backgroundColor.setBlue(b_bkgrd);
	}
	
	public void close() {
		window.destroy();
	}

	public AbstractRenderer getRenderer() {
		return renderer;
	}

	public void setRenderer(AbstractRenderer renderer) {
		this.renderer = renderer;
	}

	public void setImageFolderName(String folderName) {
		this.imageFolderName = folderName;
	}

	public void setPngMaker(PNGmaker pngMaker) {
		this.pngMaker = pngMaker;
	}
	
	public void setStimObjIds(List<Long> stimObjIds) {
		this.stimObjIds = stimObjIds;
	}
	
	public <T extends Drawable> void setStimObjs(List<T> stimObjs) {
		this.stimObjs = stimObjs;
		nStim = stimObjs.size();
	}
}
