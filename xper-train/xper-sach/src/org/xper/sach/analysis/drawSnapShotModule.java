package org.xper.sach.analysis;

// we generate this class by modifing the oGLFrame
// the main goal is to generate snapshot, and then show in java/ save in db

import java.io.*;
import java.awt.image.BufferedImage;


import java.nio.FloatBuffer;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;

//import myMathLib.JMatLinkLib;

import org.aspectj.weaver.patterns.ThisOrTargetAnnotationPointcut;
import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.*;
import org.lwjgl.input.Keyboard;
import org.lwjgl.input.Mouse;
import org.lwjgl.LWJGLException;
import org.lwjgl.Sys;
//import org.lwjgl.opengl.glu.*;
import org.lwjgl.util.glu.*;
import org.xper.sach.drawing.stimuli.BsplineObjectSpec;

//import shapeGen.ShapeSpec;
//import shapeGen.ShapeType;
//import shapeGen.mStickGen.GLImage;
//import shapeGen.mStickGen.MStickSpec;
//import shapeGen.mStickGen.MatchStick;
//import shapeGen.mStickGen.oGLDebug.Nurbs_JNI;
//import shapeGen.surfGen.SurfModel;
//import shapeGen.surfGen.SurfModelSpec;

//import javax.media.j3d.*;
//import javax.vecmath.*;

public class drawSnapShotModule {


	private final String WINDOW_TITLE;		
	private final int MAX_REFRESH_RATE;
	private final int MIN_BITS_PER_PIXEL;
	private final boolean VSYNC;
	private final boolean FULLSCREEN;

	protected final float RATIO;
	/*
	 * Static default values for constructors which don't have all parameters.
	 */
	private static final String DEFAULT_TITLE = "OpenGL with LWJGL";
	private static  int WINDOW_WIDTH = 800;
	private static  int WINDOW_HEIGHT = 800;
	private static final int DEFAULT_MAX_REFRESH_RATE = Display.getDisplayMode().getFrequency();
	private static final int DEFAULT_MIN_BITS_PER_PIXEL = Display.getDisplayMode().getBitsPerPixel();
	private static final boolean DEFAULT_VSYNC = false;
	private static final boolean DEFAULT_FULLSCREEN = false;

	private boolean onAnimation = false;
	private float animate_rotAngle = 0.0f;

	private boolean activateSurfFlag = true;
	// 	when this is false, we do not draw surf-based shape
	// 	(so, don't open matlab)
	private boolean drawNurbsFlag = false; //true, then draw NURBS
	// false then draw Stick
	private boolean showBlankMode = false; // if true, show nothing
	/// The variables related to drawing object
	//		MatchStick nowStick = new MatchStick(); 
	//		Nurbs_JNI aNurbs_JNI;

	public drawSnapShotModule() {
		this(DEFAULT_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT);
	}

	public drawSnapShotModule(String windowTitle, int windowWidth, int windowHeight) {
		this(windowTitle, windowWidth, windowHeight, DEFAULT_MAX_REFRESH_RATE,
				DEFAULT_MIN_BITS_PER_PIXEL, DEFAULT_VSYNC, DEFAULT_FULLSCREEN);
	}

	protected drawSnapShotModule(String windowTitle, int windowWidth, int windowHeight, int maxRefreshRate,
			int minBitsPerPixel, boolean vsync, boolean fullscreen) {
		WINDOW_TITLE = windowTitle; 
		WINDOW_WIDTH = windowWidth;
		WINDOW_HEIGHT = windowHeight;
		MAX_REFRESH_RATE = maxRefreshRate;
		MIN_BITS_PER_PIXEL = minBitsPerPixel;
		VSYNC = vsync;
		FULLSCREEN = fullscreen;
		RATIO = (float) WINDOW_WIDTH / (float) WINDOW_HEIGHT;	
	}


	/**
	 * Starts processing. Initializes OpenGL and calls the run() method. Before exiting, cleanup()
	 * is called.
	 */
	private void ShapeGeneration()
	{
		//	 nowStick.genMatchStickRand();
		// 	 //nowStick.genMatchStickManually();
		// 	
		// 	 if ( activateSurfFlag)
		// 	 {
		// 		aNurbs_JNI = new Nurbs_JNI();
		// 		aNurbs_JNI.init();
		// 	 }
	}

	public ImgBinData[] drawSnapShotBySpec(BsplineObjectSpec[] specList, int nShape)
	{
		ImgBinData[] result = new ImgBinData[nShape+1];
		// need to init display every time
		try{
			initDisplay();
		}
		catch (LWJGLException ex) {
			System.out.println("ERROR!!");
			System.out.println(ex.toString());
			Sys.alert(WINDOW_TITLE, "An exception occured. Exiting application.");
		}	 
		init();

		//     nowStick = new MatchStick();
		//     // make a generic template
		//     nowStick.genMatchStickRand();
		//     aNurbs_JNI = new Nurbs_JNI();
		//     
		//	  // 1. read in either the MAxis or Surf spec
		//     int i;
		//     for (i=1; i<=nShape; i++)
		//     {
		//    	 ShapeSpec inspec = specList[i];
		//    	 if (inspec.shapeType == ShapeType.MAxisShape)
		//    	 {
		//		 	MatchStick aStick = new MatchStick();
		//		 	//aStick.genMatchStickFromShapeSpec(inspec.mStickSpec);
		//		 	//nowStick.copyFrom(aStick);
		//		 	//to make it faster, I want only copy the vertex/fac info
		//		 	int nVect = inspec.mStickSpec.getNVect();
		//		 	int nFac = inspec.mStickSpec.getNFac();
		//		 	Point3d[] ivect_info = inspec.mStickSpec.getVectInfo();
		//		 	Vector3d[] inormMat_info = inspec.mStickSpec.getNormMatInfo();
		//		 	int[][] iFac_info = inspec.mStickSpec.getFacInfo();
		//		 	
		//		 	nowStick.obj1.setInfo(nVect, ivect_info, inormMat_info, nFac, iFac_info);
		//		 	this.showBlankMode = false;
		//		 	this.drawNurbsFlag = false;
		//    	 }
		//    	 else if ( inspec.shapeType == ShapeType.SurfBasedShape)
		//    	 {
		//		 	aNurbs_JNI.init_withSpec(inspec.surfModelSpec);
		//		 	this.showBlankMode = false;
		//		 	this.drawNurbsFlag = true;
		//    	 }
		//    	 else if ( inspec.shapeType == ShapeType.PolyMesh4RotInv)
		//    	 {    		 
		// 		 	int nVect = inspec.polyMeshSpec.getNVect();
		// 		 	int nFac = inspec.polyMeshSpec.getNFac();
		// 		 	Point3d[] ivect_info = inspec.polyMeshSpec.getVectInfo();
		// 		 	Vector3d[] inormMat_info = inspec.polyMeshSpec.getNormMatInfo();
		// 		 	int[][] iFac_info = inspec.polyMeshSpec.getFacInfo();
		// 		 	
		// 		 	nowStick.obj1.setInfo(nVect, ivect_info, inormMat_info, nFac, iFac_info);
		// 		 	this.showBlankMode = false;
		// 		 	this.drawNurbsFlag = false; 
		//    	 }
		//    	 else //blank or polymesh4RotInvStudy
		//    	 {
		//    		 // snap shot a blank
		//    		 this.showBlankMode = true;
		//    	 }
		//   
		//    	 // 2. update the view and then take shot
		//	 		this.render();
		//	 		Display.update();	
		//				
		//	 		// we should chg this screenShot from write to file to write in a binary vector
		//	 		int shapeId = i;
		//	 		byte[] res =this.screenShot2Binary(WINDOW_WIDTH, WINDOW_HEIGHT, shapeId);
		//	 		result[i] = new ImgBinData();
		//	 		result[i].data = res;
		//     } 
		return result;
	}
	public void go() {
		try {
			initDisplay();    
			init();
			ShapeGeneration();


			this.render();
			Display.update();   	   		 
			run();
		} catch (LWJGLException ex) {
			System.out.println(ex.toString());
			Sys.alert(WINDOW_TITLE, "An exception occured. Exiting application.");
		} finally {
			cleanup();
		}
	}

	/**
	 * Initialises the OpenGL display.
	 * 
	 * @throws org.lwjgl.LWJGLException
	 */
	protected void initDisplay() throws LWJGLException {
		// Set display mode.
		//System.out.println("h1");
		DisplayMode m = new DisplayMode(WINDOW_WIDTH, WINDOW_HEIGHT);
		Display.setDisplayMode(m);
		// Set various properties.
		//System.out.println("h2"); 	 
		Display.setTitle(WINDOW_TITLE);

		Display.setFullscreen(FULLSCREEN);

		Display.setVSyncEnabled(VSYNC);
		//System.out.println("h3");
		Display.create();
		Display.setLocation(200, 100);
		//System.out.println("h4");
		Display.makeCurrent();
	}

	/**
	 * Initialises OpenGL drawing settings.
	 */
	protected void init() {

		GL11.glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
		GL11.glMatrixMode(GL11.GL_PROJECTION);
		GL11.glLoadIdentity();
		//GL11.glOrtho(-10.0, 10.0, -10.0, 10.0, 0, 10.0);
		//GL11.glFrustum(0, 1, 0, 1, 0.01, 10);
		//GL11.glFrustum(-3, 3, -3, 3, 0.01, 100);
		GLU.gluPerspective(45.0f, (float)500.0/(float)500.0, 0.01f, 100.0f);
		GL11.glMatrixMode(GL11.GL_MODELVIEW);
		GL11.glLoadIdentity();
		GLU.gluLookAt(0.0f, 0.0f, 5.0f, 0.0f, 0.0f, 0.0f, 0.0f, 1.0f, 0.0f);
		// gluLookAt (eyeX,eyeY,eyeZ, centerX,centerY, centerZ, UpX, upY, upZ
		GL11.glScalef(0.025f, 0.025f, 0.025f);
		//GL11.glTranslatef( 0.0f, 0.0f, -10.0f);
		//			
		//		gluLookAt(-0.04,0,1, 0,0,0, 0,1,0);
		this.initLight();

		// polygon smooth trial
		boolean polySmooth = false;
		if (!polySmooth) {

			GL11.glDisable (GL11.GL_BLEND);
			GL11.glDisable (GL11.GL_POLYGON_SMOOTH);
			GL11.glEnable (GL11.GL_DEPTH_TEST);
		}
		else {

			GL11.glEnable (GL11.GL_BLEND);
			GL11.glEnable (GL11.GL_POLYGON_SMOOTH);
			GL11.glDisable (GL11.GL_DEPTH_TEST);
		}    


	}

	/**
	 * the sub function called by init() which initialize the lighting setting
	 */
	private void initLight()
	{

		float mat_shininess = .3f;
		float[] mat_ambient = { 0.0f, 0.0f, 0.0f, 1.0f};
		/*
      float[] mat_specular = {.2f, .2f, .2f, 1.0f};                  
      float[] mat_diffuse = {0.008f, 0.008f, 0.008f, 1.0f};
		 */
		float[] mat_specular = {.2f, .2f, .2f, 1.0f};                  
		float[] mat_diffuse = {0.006f, 0.006f, 0.006f, 1.0f};
		//float[] light_position = {1.0f, 1.0f, 1.0f, 0.0f};
		float[] light_position = {0.0f, 0.0f, 100.0f, 1.0f};

		FloatBuffer mat_specularBuffer = BufferUtils.createFloatBuffer(mat_specular.length);
		mat_specularBuffer.put(mat_specular).flip();

		FloatBuffer mat_ambientBuffer = BufferUtils.createFloatBuffer(mat_ambient.length);
		mat_ambientBuffer.put(mat_ambient).flip();

		FloatBuffer mat_diffuseBuffer = BufferUtils.createFloatBuffer(mat_diffuse.length);
		mat_diffuseBuffer.put(mat_diffuse).flip();

		FloatBuffer light_positionBuffer = BufferUtils.createFloatBuffer(light_position.length);        
		light_positionBuffer.put(light_position).flip();


		GL11.glMaterial(GL11.GL_FRONT, GL11.GL_SPECULAR, mat_specularBuffer);
		GL11.glMaterialf(GL11.GL_FRONT, GL11.GL_SHININESS, mat_shininess);
		GL11.glMaterial(GL11.GL_FRONT, GL11.GL_AMBIENT, mat_ambientBuffer);
		GL11.glMaterial(GL11.GL_FRONT, GL11.GL_DIFFUSE, mat_diffuseBuffer);
		GL11.glClearColor(0.0f, 0.0f, 0.0f, 0.0f);

		GL11.glLight(GL11.GL_LIGHT0, GL11.GL_POSITION, light_positionBuffer);

		//make sure white light
		float[] white_light = { 1.0f, 1.0f, 1.0f, 1.0f};
		FloatBuffer wlightBuffer = BufferUtils.createFloatBuffer( white_light.length);
		wlightBuffer.put(white_light).flip();
		GL11.glLight(GL11.GL_LIGHT0, GL11.GL_DIFFUSE, wlightBuffer);
		GL11.glLight(GL11.GL_LIGHT0, GL11.GL_SPECULAR, wlightBuffer);	

		GL11.glEnable(GL11.GL_LIGHTING);
		GL11.glEnable(GL11.GL_LIGHT0);
		GL11.glEnable(GL11.GL_DEPTH_TEST);

		GL11.glDisable(GL11.GL_BLEND);
		GL11.glDisable(GL11.GL_POLYGON_SMOOTH);


		//	GL11.glCullFace (GL11.GL_BACK);
		//	GL11.glEnable (GL11.GL_CULL_FACE);
		//GL11.glDisable(GL11.GL_LIGHTING);

		GL11.glEnable(GL11.GL_AUTO_NORMAL);

	}

	/**
	 * Does the actual drawing work. Executed after initialisation. Runs a continuous loop that
	 * calls logic() and render().
	 */
	protected void run() {
		while (!Keyboard.isKeyDown(Keyboard.KEY_ESCAPE) && !Display.isCloseRequested()) {
			if (Display.isVisible()) {
				logic();
				render();
			} else {
				if (Display.isDirty()) {
					render();
				}
				try {
					Thread.sleep(500);
				} catch (InterruptedException ex) {
				}
			}
			Display.update();
		}
	}

	/**
	 * Creates a new image that is to be displayed.
	 */
	protected void render() {
		/* clear all pixels  */
		GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT);

		/* draw white polygon (rectangle) with corners at
		 * (0.25, 0.25, 0.0) and (0.75, 0.75, 0.0)  
		 */
		GL11.glColor3f(1.0f, 0.0f, 0.0f);
		GL11.glPointSize(10.0f);

		if ( this.showBlankMode == true)
			return;

		/// draw the xyz frame basis, RGB -> xyz
		//this.drawAxis();

		if ( this.onAnimation)
		{
			GL11.glPushMatrix();
			this.animate_rotAngle += 2.0f;
			GL11.glRotatef( this.animate_rotAngle, 1.0f, 0.0f, 0.0f);
		}
		//	 if ( drawNurbsFlag)
		//	 {			
		//		 aNurbs_JNI.drawNurbs();
		//	 }
		//	 else
		//		 nowStick.drawSkeleton();
		GL11.glFlush();

		if (this.onAnimation)
			GL11.glPopMatrix();
	}


	/**
	 *
	draw the Axis to help us clarify the coordinate system
	 */
	private void drawAxis()
	{
		float axisLen = 8.0f;
		GL11.glDisable(GL11.GL_LIGHTING);
		GL11.glBegin(GL11.GL_LINES);
		GL11.glColor3f(1.0f, 0.0f, 0.0f);
		//GL11.glVertex3f(- axisLen, 0.0f, 0.0f);        
		GL11.glVertex3f(0.0f, 0.0f, 0.0f);
		GL11.glVertex3f( axisLen, 0.0f, 0.0f);

		GL11.glColor3f(0.0f, 1.0f, 0.0f); 	     
		//GL11.glVertex3f(0.0f, -axisLen, 0.0f);	
		GL11.glVertex3f(0.0f,  0.0f, 0.0f);
		GL11.glVertex3f(0.0f, axisLen, 0.0f);

		GL11.glColor3f(0.0f, 0.0f, 1.0f);
		//GL11.glVertex3f(0.0f, 0.0f, -axisLen);
		GL11.glVertex3f(0.0f, 0.0f, 0.0f);
		GL11.glVertex3f(0.0f, 0.0f, axisLen);
		GL11.glEnd();

		//draw a dot at (0,0, -5) and (0,0,0), and (0,0,5)
		GL11.glColor3f( 1.0f, 0.0f, 0.0f);
		GL11.glPointSize(6.0f);
		GL11.glBegin(GL11.GL_POINTS);
		GL11.glVertex3f( 0.0f, 0.0f, 0.0f);
		//  GL11.glVertex3f( 0.0f, 0.0f, 5.0f);
		GL11.glVertex3f( 0.0f, 0.0f, -5.0f);
		GL11.glEnd();

		GL11.glEnable(GL11.GL_LIGHTING);


	}
	/**
	 * Handles logic that does not concern rendering, e.g. animation.
	 */
	protected void logic() {
		int eventKey;

		if ( Mouse.next())
		{


			int dx = Mouse.getEventDX();
			int dy = Mouse.getEventDY();

			if ( Mouse.isButtonDown(0) ) // only rot if the button is down
			{
				if ( dx > 0)
					GL11.glRotatef (1.5f, 0.0f, 1.0f, 0.0f);
				else if ( dx < 0)
					GL11.glRotatef (-1.5f, 0.0f, 1.0f, 0.0f);

				if ( dy > 0)
					GL11.glRotatef (-1.5f, 1.0f, 0.0f, 0.0f);
				else if ( dy < 0)
					GL11.glRotatef (1.5f, 1.0f, 0.0f, 0.0f);
			}

		}

		Keyboard.enableRepeatEvents(true);
		while (Keyboard.next()) {
			eventKey = Keyboard.getEventKey();
			if (eventKey == Keyboard.KEY_L  && Keyboard.isKeyDown(Keyboard.KEY_L))
			{
				//read all the population shapes, and then save their image files
				long shapeId = 1;
				long viewId = 1;
			}   

			//		if (eventKey == Keyboard.KEY_R  && Keyboard.isKeyDown(Keyboard.KEY_R))
			//		{
			//			//read from a file
			//			nowStick.genMatchStickFromFileData(); 		
			//		}
			//		if (eventKey == Keyboard.KEY_E  && Keyboard.isKeyDown(Keyboard.KEY_E))
			//		{
			//			//use the manually generating function to generate the MSTICK shape
			//			nowStick.genMatchStickManually();
			//		}    
			//
			//		if (eventKey == Keyboard.KEY_A  && Keyboard.isKeyDown(Keyboard.KEY_A))
			//		{
			//			//generate a new shape
			//			nowStick.genMatchStickRand();
			//		}
			//		if (eventKey == Keyboard.KEY_Z  && Keyboard.isKeyDown(Keyboard.KEY_Z))
			//		{
			//			//generate a new shape
			//			//nowStick.genMatchStickRand();
			//			while(true)
			//				if ( nowStick.mutate(1) )
			//					break;
			//			// randomly mutate to a possible son, (param = 1 --> remove 1)
			//		}
			//		if (eventKey == Keyboard.KEY_X  && Keyboard.isKeyDown(Keyboard.KEY_X))
			//		{
			//			while(true)
			//				if ( nowStick.mutate(2) )
			//					break;
			//			// randomly mutate to a possible son (param = 2 --> add 1)
			//		}
			//		if (eventKey == Keyboard.KEY_C  && Keyboard.isKeyDown(Keyboard.KEY_C))
			//		{
			//
			//			while(true)
			//				if ( nowStick.mutate(3) )
			//					break;
			//			// randomly mutate to a possible son (param = 3 --> replace 1)
			//		}
			//		if (eventKey == Keyboard.KEY_S  && Keyboard.isKeyDown(Keyboard.KEY_S))
			//		{
			//
			//			while(true)
			//				if ( nowStick.mutate(4) )
			//					break;
			//			// randomly mutate to a possible son (param = 4 --> fine tune 1)
			//		}
			//		if (eventKey == Keyboard.KEY_D  && Keyboard.isKeyDown(Keyboard.KEY_D))
			//		{
			//			MatchStick newOne = new MatchStick();
			//			ShapeSpec tempSpec  = new ShapeSpec();
			//			tempSpec.setMAxisSpec(nowStick);
			//			newOne.genMatchStickFromShapeSpec(tempSpec.mStickSpec);
			//
			//			while (true)
			//				if ( newOne.mutate(0))
			//					break;
			//
			//			nowStick.copyFrom(newOne);
			//			System.out.println("nowstick final rot"+ nowStick.finalRotation[0] + " " + nowStick.finalRotation[1] + nowStick.finalRotation[2]);
			//			/*
			//	    	while(true)
			//	    		if ( nowStick.mutate(0) )
			//	    			break;
			//			 */
			//			// randomly mutate to a possible son
			//		}
			//		if (eventKey == Keyboard.KEY_B  && Keyboard.isKeyDown(Keyboard.KEY_B))
			//		{
			//			nowStick.setBackToParent();
			//		}
			if (eventKey == Keyboard.KEY_V && Keyboard.isKeyDown(Keyboard.KEY_V)) {
				GL11.glRotatef (4.0f, 1.0f, 0.0f, 0.0f);		
			}
			if (eventKey == Keyboard.KEY_N && Keyboard.isKeyDown(Keyboard.KEY_N)) {
				GL11.glRotatef (4.0f, 0.0f, 1.0f, 0.0f);		 
			}
			if (eventKey == Keyboard.KEY_O && Keyboard.isKeyDown(Keyboard.KEY_O)) {
				GL11.glRotatef (4.0f, 0.0f, 0.0f, 1.0f);		
			}
			if (eventKey == Keyboard.KEY_ADD) { //&& Keyboard.isKeyDown(Keyboard.KEY_ADD)) {
				GL11.glScalef(1.1f, 1.1f, 1.1f);

			}
			//		if (eventKey == Keyboard.KEY_U  && Keyboard.isKeyDown(Keyboard.KEY_U)) {
			//			drawNurbsFlag = ! drawNurbsFlag;
			//
			//			//when we want to write a random surf-shape
			//
			//			ShapeSpec nowspec = new ShapeSpec();
			//			nowspec.setSurfModelSpec(aNurbs_JNI.surf_model);			
			//			nowspec.setStimId_LabelAndGen(1, 1, -1, -1);					
			//			String fname = "./test2.xml";
			//			nowspec.writeInfo2File(fname);
			//
			//
			//		}
			//		if (eventKey == Keyboard.KEY_Y  && Keyboard.isKeyDown(Keyboard.KEY_Y)) {
			//			aNurbs_JNI.init();   	    	                     
			//		}
			//		if (eventKey == Keyboard.KEY_T  && Keyboard.isKeyDown(Keyboard.KEY_T)) {
			//			aNurbs_JNI.mutate();   	    	                     
			//		}
			//
			//		if (eventKey == Keyboard.KEY_Q) { //&& Keyboard.isKeyDown(Keyboard.KEY_ADD)) {
			//			nowStick.showMode = 0;// (nowStick.showMode +1) % 2;
			//
			//		}
			//		if (eventKey == Keyboard.KEY_W) { //&& Keyboard.isKeyDown(Keyboard.KEY_ADD)) {
			//			nowStick.showMode = 1;// (nowStick.showMode +1) % 2;
			//
			//		}
			if (eventKey == Keyboard.KEY_SUBTRACT && Keyboard.isKeyDown(Keyboard.KEY_SUBTRACT)) {
				GL11.glScalef(.9f, .9f, .9f);
			}

			if (eventKey == Keyboard.KEY_P && Keyboard.isKeyDown(Keyboard.KEY_P)) {
				// take screen shot
				//this.screenShot(WINDOW_WIDTH, WINDOW_HEIGHT, "nowOut.png");
				this.screenShot(WINDOW_WIDTH, WINDOW_HEIGHT, "");
			}        

			//animation
			if ( eventKey == Keyboard.KEY_M && Keyboard.isKeyDown(Keyboard.KEY_M))
			{
				this.onAnimation = true;
				this.animate_rotAngle = 0.0f;
				// rotate the shape animation on or off
				for (int i=0; i<180; i++)
				{
					//GL11.glRotatef (2.5f, 1.0f, 0.0f, 0.0f);
					try{  		Thread.sleep(33); }
					catch (Exception e) {System.out.println("err");}
					this.render();
					Display.update();
				}
				this.onAnimation = false;
			}
		}
	}


	/**
	locate memory, subFunction of screenShot
	 */
	public static ByteBuffer allocBytes(int howmany) {
		final int SIZE_BYTE = 4;
		return ByteBuffer.allocateDirect(howmany * SIZE_BYTE).order(ByteOrder.nativeOrder());
	}

	/**
	 *   taking the screen shot, return the binary array, don't save file
	 */

	private byte[] screenShot2Binary(int width, int height, int shapeId) 
	{
		// allocate space for RBG pixels
		//System.out.print("In screenShot to binary\n");

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
					| ((framebytes.get(bindex) & 0x000000FF) << 16)     // R
					| ((framebytes.get(bindex+1) & 0x000000FF) << 8)    // G
					| ((framebytes.get(bindex+2) & 0x000000FF) << 0);   // B
		}
		// free up this memory
		framebytes = null;
		// flip the pixels vertically (opengl has 0,0 at lower left, java is upper left)
		//		pixels = GLImage.flipPixels(pixels, width, height);

		try {
			ByteArrayOutputStream out = new ByteArrayOutputStream();
			// Create a BufferedImage with the RGB pixels then save as PNG
			BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
			image.setRGB(0, 0, width, height, pixels, 0, width);


			//javax.imageio.ImageIO.write(image, "png", new File(saveFilename));

			javax.imageio.ImageIO.write(image, "png", out);
			byte[] data = out.toByteArray();

			//System.out.println("the img data length is " + data.length);

			// I decide to also save the file to harddisk this moment
			// since it will be easier to read from Matlab
			String saveFilename = "./matlabSimpleAnalysis/matlabPng/" + Integer.toString(shapeId) + ".png";

			//for conveninent get pop shape correct name

			//	if (shapeId > 50)
			//		saveFilename = "./matlabPng/pop" + Integer.toString(shapeId-50) + ".png";
			javax.imageio.ImageIO.write(image, "png", new File(saveFilename));
			return data;


		}
		catch (Exception e) {
			System.out.println("screenShot(): exception " + e);
			return null;
		}
	}
	/*                 
	Taking the screen shot
	 */
	public void screenShot(int width, int height, String saveFilename) 
	{
		// allocate space for RBG pixels
		System.out.print("In screenShot\n");
		if ( saveFilename.length() == 0)
		{
			System.out.println("file name not given");
			// determine the file name by a sequential serial #
			try 
			{
				String aFile = "./img/count.txt";
				BufferedReader input =  new BufferedReader(new FileReader(aFile));      
				String line = null; //not declared within while loop        
				line = input.readLine();
				input.close();
				int count = Integer.valueOf(line).intValue();
				System.out.println("the line is "+ line);
				System.out.println("Now the serial count " + count);

				// generate teh saveFilename
				saveFilename = "./img/Img"+count+".png";

				// now rewrite the count.txt file
				count++;

				Writer output = new BufferedWriter(new FileWriter(aFile));

				//FileWriter always assumes default encoding is OK!
				String outStr = "" + count;
				output.write( outStr );
				output.close();	 
			}
			catch (IOException ex){
				System.out.println("Error open index file count.txt");  }
		}

		ByteBuffer framebytes = allocBytes(width * height * 3);
		//	ByteBuffer framebytes = new ByteBuffer();
		//final int SIZE_BYTE = 4;
		//framebytes.allocateDirect( width*height*3 * SIZE_BYTE).order(ByteOrder.nativeOrder());



		int[] pixels = new int[width * height];
		int bindex;
		// grab a copy of the current frame contents as RGB (has to be UNSIGNED_BYTE or colors come out too dark)
		GL11.glReadPixels(0, 0, width, height, GL11.GL_RGB, GL11.GL_UNSIGNED_BYTE, framebytes);
		// copy RGB data from ByteBuffer to integer array
		for (int i = 0; i < pixels.length; i++) {
			bindex = i * 3;
			pixels[i] =
					0xFF000000                                          // A
					| ((framebytes.get(bindex) & 0x000000FF) << 16)     // R
					| ((framebytes.get(bindex+1) & 0x000000FF) << 8)    // G
					| ((framebytes.get(bindex+2) & 0x000000FF) << 0);   // B
		}
		// free up this memory
		framebytes = null;
		// flip the pixels vertically (opengl has 0,0 at lower left, java is upper left)
		//     pixels = GLImage.flipPixels(pixels, width, height);

		try {
			ByteArrayOutputStream out = new ByteArrayOutputStream();
			// Create a BufferedImage with the RGB pixels then save as PNG
			BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
			image.setRGB(0, 0, width, height, pixels, 0, width);

			javax.imageio.ImageIO.write(image, "png", new File(saveFilename));

			//          ImageIO.write(image, "png", out);
			//          byte[] data = out.toByteArray();
			//
			//	System.out.println("the data length is " + data.length);
			//
			//	    File outFile = new File("./nowScShot.png");
			// 	    BufferedOutputStream bos = new BufferedOutputStream(new FileOutputStream(outFile));             
			//
			//              bos.write(data, 0, data.length);			         
			//    		bos.flush();
			//    		bos.close();
			// we should write the Data into a file
			//dbUtil.writeThumbnail(stimId,data);

		}
		catch (Exception e) {
			System.out.println("screenShot(): exception " + e);
		}
	}


	/**
	 * Executed before the application exits to clean up the display, etc.
	 */
	protected void cleanup() {
		Display.destroy();
	}



	// a debug main
	public static void main(String[] args) {

		System.out.println("test drawSnapShotModule");

		drawSnapShotModule snapper = new drawSnapShotModule("snap shot", 400,400);
		snapper.go();

		//     SurfModel.closeJMatLinkEngine();
	}
}
