package org.xper.allen.drawing.composition;

import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.PixelFormat;
import org.xper.alden.drawing.drawables.BaseWindow;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.alden.drawing.renderer.AbstractRenderer;
import org.xper.alden.drawing.renderer.PerspectiveRenderer;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper;
import org.xper.allen.drawing.composition.noisy.NoiseMapCalculation;
import org.xper.allen.drawing.composition.noisy.NAFCNoiseMapper;
import org.xper.allen.drawing.ga.Thumbnailable;
import org.xper.util.ThreadUtil;

import javax.imageio.ImageIO;

public class AllenDrawingManager implements Drawable {
	private final NAFCNoiseMapper noiseMapper;
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

	public BaseWindow window;

	public AbstractRenderer renderer;




	public AllenDrawingManager(int width, int height, NAFCNoiseMapper noiseMapper) {
		super();
		this.width = width;
		this.height = height;
		this.noiseMapper = noiseMapper;
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
		renderer.setDepth(pngMaker.getDepth());
		renderer.setDistance(pngMaker.getDistance()); //TODO: stitch this into generator so it is a dependency
		double rendererMM = pngMaker.getDpiUtil().calculateMmForRenderer();
		renderer.setPupilDistance(pngMaker.getPupilDistance());
		renderer.setHeight(rendererMM);
		renderer.setWidth(rendererMM);
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
	public String drawCompGraphNoiseMap(AllenMatchStick obj, Long stimObjId, List<String> additionalLabels) {
		LinkedList<String> labels = new LinkedList<>();
		labels.add("noisemap");
		labels.addAll(additionalLabels);
		GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT | GL11.GL_STENCIL_BUFFER_BIT);
		GL11.glClearColor(r_bkgrd, g_bkgrd, b_bkgrd, 1);
		renderer.draw(new Drawable() {
			@Override
			public void draw() {
				// TODO Auto-generated method stub
				drawCompGraphNoiseMap(obj);
			}
		});

		window.swapBuffers();
		return pngMaker.saveImage(stimObjId,labels,height,width, imageFolderName);
	}

	public String drawNoiseMap(ProceduralMatchStick obj, Long stimObjId, List<String> additionalLabels, double amplitude, int specialCompIndx) throws IOException {
		return drawNoiseMap(obj, stimObjId, additionalLabels, amplitude, Collections.singletonList(specialCompIndx));
	}

	public String drawNoiseMap(ProceduralMatchStick obj, Long stimObjId, List<String> additionalLabels, double amplitude, List<Integer> specialCompIdcs) throws IOException {
		LinkedList<String> labels = new LinkedList<>();
		labels.addAll(additionalLabels);
		labels.add("noisemap");

		String path = imageFolderName + "/" + stimObjId;
		for (String str:labels) {
			if(!str.isEmpty()) {
				path=path+"_"+str;
			}
		}
		path=path+".png";

		return noiseMapper.mapNoise(obj, amplitude, specialCompIdcs, renderer, path);
	}

	public String drawGaussNoiseMap(ProceduralMatchStick obj, Long stimObjId, List<String> additionalLabels, double amplitude, int specialCompIndx) throws IOException {
		LinkedList<String> labels = new LinkedList<>();
		labels.addAll(additionalLabels);
		labels.add("noisemap");

		BufferedImage img = ((GaussianNoiseMapper) noiseMapper).generateGaussianNoiseMapFor(obj,
				width, height,
				amplitude, 0, renderer, specialCompIndx);
		String path = imageFolderName + "/" + stimObjId;
		for (String str:labels) {
			if(!str.isEmpty())
				path=path+"_"+str;
		}
		path=path+".png";
		File ouptutFile = new File(path);
		ImageIO.write(img, "png", ouptutFile);
		return ouptutFile.getAbsolutePath();
	}

	public String drawCompMap(AllenMatchStick obj, Long stimObjId, List<String> labels) {
		labels.add("compmap");
		GL11.glClearColor(r_bkgrd,g_bkgrd,b_bkgrd,1);
		GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT | GL11.GL_STENCIL_BUFFER_BIT);
		renderer.draw(new Drawable() {
			@Override
			public void draw() {
				obj.drawCompMap();
			}
		});

		window.swapBuffers();
		return pngMaker.saveImage(stimObjId, labels, height, width, imageFolderName);
	}

	/**
	 * Draws single png of obj using window that is already open.
	 * @param obj
	 * @param stimObjId
	 * @param labels
	 * @return
	 */
	public String drawStimulus(Drawable obj, Long stimObjId, List<String> labels) {
		ThreadUtil.sleep(100);
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

	public String drawThumbnail(Thumbnailable obj, Long stimObjId, List<String> labels) {
		labels.add("thumbnail");
		ThreadUtil.sleep(100);
		GL11.glClearColor(r_bkgrd,g_bkgrd,b_bkgrd,1);
		GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT | GL11.GL_STENCIL_BUFFER_BIT);
		renderer.draw(new Drawable() {
			@Override
			public void draw() {
				obj.drawThumbnail(renderer.getWidth(), renderer.getHeight());
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

	public void drawObj(Drawable obj) {
		obj.draw();
	}



	public void drawCompGraphNoiseMap(AllenMatchStick obj) {
		GL11.glClearColor(r_bkgrd,g_bkgrd,b_bkgrd,1);
		GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT | GL11.GL_STENCIL_BUFFER_BIT);
		obj.drawGraphNoiseMap(new NoiseMapCalculation(obj, obj.noiseChanceBounds, obj.noiseNormalizedPositions));
	}

	public void drawCompGraphNoiseMap() {
		if (nStim > 0) {
			stimObjs.get(stimCounter).drawGraphNoiseMap(new NoiseMapCalculation(stimObjs.get(stimCounter), stimObjs.get(stimCounter).noiseChanceBounds, stimObjs.get(stimCounter).noiseNormalizedPositions));
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