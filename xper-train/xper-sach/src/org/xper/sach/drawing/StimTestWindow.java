package org.xper.sach.drawing;

import java.util.ArrayList;
import java.util.List;

import org.lwjgl.opengl.Display;
import org.lwjgl.opengl.DisplayMode;
import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.PixelFormat;
//import org.xper.ManualTest;
import org.xper.XperConfig;
import org.xper.console.CommandListener;
import org.xper.drawing.Context;
import org.xper.drawing.Drawable;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveRenderer;
import org.xper.sach.analysis.PNGmaker;
import org.xper.sach.drawing.screenobj.SimpleText;
import org.xper.sach.drawing.splines.MyPoint;
import org.xper.sach.drawing.stimuli.BsplineObject;
import org.xper.time.DefaultTimeUtil;
import org.xper.time.TimeUtil;
//import org.xper.util.ThreadUtil;

//@ManualTest
public class StimTestWindow implements CommandListener, Drawable {
	boolean done = false;
	float angle = 0;
	Drawable stimObj;
	List<BsplineObject> stimObjs = new ArrayList<BsplineObject>();
	List<Long> stimObjIds = new ArrayList<Long>();			// need this for saving ids to db

	int numStims = 0;					// number of stimuli
	int stimCounter = 0;				// keeps track when drawing stimuli
	boolean gridOn = false;
	boolean drawStimNum = true;
	float r_bkgrd = 0.5f;//(float)238/255;
	float g_bkgrd = 0.5f;//(float)238/255;
	float b_bkgrd = 0.5f;//(float)238/255;
	double speedInSecs = 0.01;

	String imageFolderName = "";

	int height = 300;
	int width = 300;
	double magLevel = 3;

	boolean doPause = false;
	boolean savePNGtoDb = false;
	boolean savePNGtoFolder = false;

	PNGmaker pngMaker;

	TestingWindow window;
	AbstractRenderer renderer;

	public StimTestWindow() {
		super();
		DisplayMode mode = Display.getDisplayMode();
		width = mode.getWidth() / 2;
		height = mode.getHeight() / 2;
	}

	public StimTestWindow(int height, int width) {
		super();
		this.height = height;
		this.width = width;
	}

	public StimTestWindow(int height, int width,double mag) {
		super();
		this.height = height;
		this.width = width;
		this.magLevel = mag;
	}

	public static void main(String[] args) {
		new StimTestWindow().testDraw();
	}

	public void testDraw() {
		List<String> libs = new ArrayList<String>();
		libs.add("xper");
		new XperConfig("", libs);

		window = new TestingWindow(height,width);
		ArrayList<CommandListener> commandListeners = new ArrayList<CommandListener>();
		commandListeners.add(this);
		window.setCommandListeners(commandListeners);
		PixelFormat pixelFormat = new PixelFormat(0, 8, 1, 4);
		window.setPixelFormat(pixelFormat);
		window.create();

		renderer = new PerspectiveRenderer();
		renderer.setDepth(6000);
		renderer.setDistance(525);
		renderer.setPupilDistance(34.925);
		renderer.setHeight(height/magLevel);
		renderer.setWidth(width/magLevel);
		try {
			Thread.sleep(100);
		} catch (InterruptedException e) {
			throw new RuntimeException(e);
		}
		renderer.init(window.getWidth(), window.getHeight());
		Context context = new Context();

		GL11.glShadeModel(GL11.GL_SMOOTH);
		GL11.glDisable(GL11.GL_DEPTH_TEST);

		TimeUtil t = new DefaultTimeUtil();

		//int i = 0;
		long startTime = t.currentTimeMicros();
		if (doPause) window.setPaused(true);
		else window.setPaused(false);

		// set background color:
		GL11.glClearColor(r_bkgrd,g_bkgrd,b_bkgrd,0);

		while(!done) {
			GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT | GL11.GL_STENCIL_BUFFER_BIT);
			GL11.glClearColor(r_bkgrd,g_bkgrd,b_bkgrd,0);
			renderer.draw(this, context);
			window.swapBuffers();
			if (t.currentTimeMicros() >= startTime + speedInSecs*1000000) {
				//ThreadUtil.sleep(2000);

				if (stimCounter < numStims && !window.isPaused()) {
					if (doPause) {
						window.setPaused(true);
					}
//					System.out.println("this is " + stimCounter);
					// call PNGmaker here!
					if (savePNGtoDb) {
						// ? call PNGmaker method to save current screen and stimObjId
						pngMaker.makePNGfromScreenShot(stimObjIds.get(stimCounter),height,width, imageFolderName);
						BsplineObject bso = (BsplineObject)stimObjs.get(stimCounter);
					}
					if (savePNGtoFolder) {
						// ? call PNGmaker method to save current screen and stimObjId
						 pngMaker.makePNGfromScreenShot_folderSaveOnly(stimObjIds.get(stimCounter),height,width, imageFolderName);
					}
					stimCounter++;
				}

				startTime = t.currentTimeMicros();
			}
			if (stimCounter >= numStims) {
				experimentStop();
			}

		}
		//window.destroy();
	}

	public void draw(Context context) {
		// set background color:
		GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT | GL11.GL_STENCIL_BUFFER_BIT);
		GL11.glClearColor(r_bkgrd,g_bkgrd,b_bkgrd,0);

		// draw grid:
		if (gridOn) {
			// draw dashed lines
				// major axes
			double xMax = context.getRenderer().getWidth()/2;
			double yMax = context.getRenderer().getHeight()/2;
			//System.out.println("w="+xMax+" h="+yMax);
			GL11.glColor3f(0.3f,0.3f,0.3f);
			GL11.glLineWidth(1f);
			drawDashLine2(new MyPoint(0,-yMax),new MyPoint(0,yMax));
			drawDashLine2(new MyPoint(-xMax,0),new MyPoint(xMax,0));
			//drawDashLine(0,-yMax,0,yMax);
			//drawDashLine(-xMax,0,xMax,0);
				// minor lines
			GL11.glColor3f(0.4f,0.4f,0.4f);
			int gridWidth = 5;
			for (int n = 1; n <= Math.ceil(xMax/gridWidth)-1; n++) {
				int m = n*gridWidth;
				//drawDashLine(m,-yMax,m,yMax);
				//drawDashLine(-m,-yMax,-m,yMax);
				drawDashLine2(new MyPoint(m,-yMax),new MyPoint(m,yMax));
				drawDashLine2(new MyPoint(-m,-yMax),new MyPoint(-m,yMax));
			}
			for (int n = 1; n <= Math.ceil(yMax/gridWidth)-1; n++) {
				int m = n*gridWidth;
				//drawDashLine(-xMax,m,xMax,m);
				//drawDashLine(-xMax,-m,xMax,-m);
				drawDashLine2(new MyPoint(-xMax,m),new MyPoint(xMax,m));
				drawDashLine2(new MyPoint(-xMax,-m),new MyPoint(xMax,-m));
			}
		}

		// draw stim from stimObj array:
		if (numStims > 0) {
			stimObjs.get(stimCounter).draw(context);
		}

		// draw stim number:
		if (drawStimNum) {
			GL11.glColor3f(1.0f,1.0f,0.0f);
			double xMax = context.getRenderer().getWidth()/2;
			double yMax = context.getRenderer().getHeight()/2;
			SimpleText.drawString(Integer.toString(stimCounter),(float)-xMax*9/10,(float)yMax*9/10);
		}
	}

	void drawLine(MyPoint p1, MyPoint p2) {
	    GL11.glBegin(GL11.GL_LINES);
	    	GL11.glVertex2d(p1.x, p1.y);
	    	GL11.glVertex2d(p2.x, p2.y);
	    GL11.glEnd();
	    GL11.glFlush();
	}

	// draw dash lines
	void drawDashLine2(MyPoint p1, MyPoint p2) {
		GL11.glLineStipple(1,(short)0x1111);
		GL11.glEnable(GL11.GL_LINE_STIPPLE);
		GL11.glBegin(GL11.GL_LINES);
			GL11.glVertex2d(p1.x, p1.y);
			GL11.glVertex2d(p2.x, p2.y);
		GL11.glEnd();
		GL11.glFlush();
		GL11.glDisable(GL11.GL_LINE_STIPPLE);
	}


	protected void drawDashLine(double x1, double y1, double x2, double y2) {
		final float seg = 1;
		double x, y;

		if (x1 == x2) {
			if (y1 > y2) {
				double tmp = y1;
				y1 = y2;
				y2 = tmp;
			}
			y = y1;
			while (y < y2) {
				double y0 = Math.min(y+seg, y2);
				drawLine(new MyPoint(x1,y),new MyPoint(x2,y0));
				//g.drawLine(x1, (int)y, x2, (int)y0);
				y = y0 + seg;
			}
			return;
		}
		else if (x1 > x2) {
			double tmp = x1;
			x1 = x2;
			x2 = tmp;
			tmp = y1;
			y1 = y2;
			y2 = tmp;
		}
		double ratio = 1.0*(y2-y1)/(x2-x1);
		double ang = Math.atan(ratio);
		double xinc = seg * Math.cos(ang);
		double yinc = seg * Math.sin(ang);
		x = x1;
		y = y1;

		while ( x <= x2 ) {
			double x0 = x + xinc;
			double y0 = y + yinc;
			if (x0 > x2) {
				x0 = x2;
				y0  = y + ratio*(x2-x);
			}
			drawLine(new MyPoint(x,y),new MyPoint(x0,y0));
			x = x0 + xinc;
			y = y0 + yinc;
		}
	}

	public void experimentPause() {
		//window.fireExperimentPause();
	}

	public void experimentResume() {
		//window.fireExperimentResume();
	}

	public void experimentStop() {
		done = true;
	}

	public void close() {
		window.destroy();
	}

	public void setStimObjs(List<BsplineObject> stimObjs) {
		this.stimObjs = stimObjs;
		for (BsplineObject obj : stimObjs) {
			obj.doCenterShape(true);
			obj.doDrawOccluder(false);
		}
		numStims = stimObjs.size();
	}

	public void setStimObjs(Drawable stimObj) {
		this.stimObjs.add((BsplineObject)stimObj);
		numStims++;
	}

	public void setGridOn(boolean gridOn) {
		this.gridOn = gridOn;
	}

	public void setBackgroundColor(float r_bkgrd,float g_bkgrd,float b_bkgrd) {
		this.r_bkgrd = r_bkgrd;
		this.g_bkgrd = g_bkgrd;
		this.b_bkgrd = b_bkgrd;
	}

	public void setBackgroundGray(float grayLevel) {
		this.r_bkgrd = grayLevel;
		this.g_bkgrd = grayLevel;
		this.b_bkgrd = grayLevel;
	}

	public void setSpeedInSecs(double s) {
		speedInSecs = s;
	}

	public AbstractRenderer getRenderer() {
		return renderer;
	}

	public void setRenderer(AbstractRenderer renderer) {
		this.renderer = renderer;
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

	public void setImageFolderName(String folderName) {
		this.imageFolderName = folderName;
	}

	public String getImageFolderName() {
		return this.imageFolderName;
	}

	public void setDoPause(boolean bool) {
		doPause = bool;
	}

	public void setPause(boolean bool) {
		window.setPaused(bool);
	}

	public void setSavePNGtoDb(boolean bool) {
		savePNGtoDb = bool;
	}

	public void setSavePNGtoFolder(boolean bool) {
		savePNGtoFolder = bool;
	}

	public PNGmaker getPngMaker() {
		return pngMaker;
	}

	public void setPngMaker(PNGmaker pngMaker) {
		this.pngMaker = pngMaker;
	}

	public void setStimObjIds(long stimObjId) {
		this.stimObjIds.add(stimObjId);
	}

	public void setStimObjIds(List<Long> stimObjIds) {
		this.stimObjIds = stimObjIds;
	}
}
