package org.xper.allen.drawing.composition;

import java.util.ArrayList;
import java.util.LinkedList;
import java.util.List;

import org.lwjgl.opengl.Display;
import org.lwjgl.opengl.DisplayMode;
import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.PixelFormat;
import org.xper.Dependency;
import org.xper.alden.drawing.drawables.BaseWindow;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.alden.drawing.renderer.AbstractRenderer;
import org.xper.alden.drawing.renderer.PerspectiveRenderer;

public class AllenDrawingManager implements Drawable {
	Drawable stimObj;

	List<AllenMatchStick> stimObjs = new ArrayList<>();
	List<Long> stimObjIds = new ArrayList<Long>();
	List<List<String>> labels = new ArrayList<>();
	int nStim = 0;
	int stimCounter = 0;
	float r_bkgrd;
	float g_bkgrd;
	float b_bkgrd;

	String imageFolderName = "";

	int height;
	int width;

	AllenPNGMaker pngMaker;

	BaseWindow window;
	@Dependency
	AbstractRenderer renderer;


	public AllenDrawingManager(int height, int width) {
		super();
		this.height = height;
		this.width = width;
	}

	/**
	 * Initializes a window to draw in. 
	 */
	public void init() {
		window = new BaseWindow(width,height);
		PixelFormat pixelFormat = new PixelFormat(0, 8, 1, 4);
		window.setPixelFormat(pixelFormat);
		window.create();

		renderer = new PerspectiveRenderer();
		//renderer = new OrthographicRenderer();
		renderer.setDepth(pngMaker.getDepth());
		renderer.setDistance(pngMaker.getDistance()); //TODO: stitch this into generator so it is a dependency
		renderer.setPupilDistance(pngMaker.getPupilDistance());
		//renderer.setHeight(height);
		//renderer.setWidth(width);
		renderer.setHeight(pngMaker.getDpiUtil().calculateMmForRenderer());
		renderer.setWidth(pngMaker.getDpiUtil().calculateMmForRenderer());
		renderer.init(window.getWidth(), window.getHeight());
		GL11.glShadeModel(GL11.GL_SMOOTH);
		GL11.glDisable(GL11.GL_DEPTH_TEST);

		GL11.glClearColor(r_bkgrd,g_bkgrd,b_bkgrd,1);
	}

	/**
	 * Draw single noise map using window that is already open. 
	 * @param obj
	 * @param stimObjId
	 * @param additionalLabels
	 * @return
	 */
	public String drawNoiseMap(AllenMatchStick obj, Long stimObjId, List<String> additionalLabels) {
		LinkedList<String> labels = new LinkedList<>();
		labels.add("noisemap");
		labels.addAll(additionalLabels);
		GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT | GL11.GL_STENCIL_BUFFER_BIT);
		GL11.glClearColor(r_bkgrd, g_bkgrd, b_bkgrd, 1);
		renderer.draw(new Drawable() {
			@Override
			public void draw() {
				// TODO Auto-generated method stub
				drawNoiseMap(obj);
			}
		});

		window.swapBuffers();
		return pngMaker.saveImage(stimObjId,labels,height,width, imageFolderName);
	}

	/**
	 * Draws single png of obj using window that is already open. 
	 * @param obj
	 * @param stimObjId
	 * @param labels
	 * @return
	 */
	public String drawStimulus(AllenMatchStick obj, Long stimObjId, List<String> labels) {
		GL11.glClearColor(r_bkgrd,g_bkgrd,b_bkgrd,1);
		GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT | GL11.GL_STENCIL_BUFFER_BIT);
		renderer.draw(new Drawable() {
			@Override
			public void draw() {
				drawObj(obj);
			}
		});

		window.swapBuffers();
		return pngMaker.saveImage(stimObjId, labels, height, width, imageFolderName);
	}


	public void draw() {
		if (nStim > 0) {
			stimObjs.get(stimCounter).draw();
		}
	}

	public void drawObj(AllenMatchStick obj) {
		obj.draw();
	}



	public void drawNoiseMap(AllenMatchStick obj) {
		GL11.glClearColor(r_bkgrd,g_bkgrd,b_bkgrd,1);
		GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT | GL11.GL_STENCIL_BUFFER_BIT);
		obj.drawNoiseMap();
	}

	public void drawNoiseMap() {
		if (nStim > 0) {
			stimObjs.get(stimCounter).drawNoiseMap();
		}
	}

	public void setBackgroundColor(float r_bkgrd,float g_bkgrd,float b_bkgrd) {
		this.r_bkgrd = r_bkgrd;
		this.g_bkgrd = g_bkgrd;
		this.b_bkgrd = b_bkgrd;
	}

	public void close() {
		window.destroy();
	}

	public boolean isOpen(){
		return window.isOpen();
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

	public void setPngMaker(AllenPNGMaker pngMaker) {
		this.pngMaker = pngMaker;
	}

	public void setStimObjIds(List<Long> stimObjIds) {
		this.stimObjIds = stimObjIds;
	}

	public void setStimObjs(List<AllenMatchStick> stimObjs) {
		this.stimObjs = stimObjs;
		nStim = stimObjs.size();
	}

	public void setBackgroundColor(double d, double e, double f) {
		this.r_bkgrd = (float) d;
		this.g_bkgrd = (float) e;
		this.b_bkgrd = (float) f;

	}
}