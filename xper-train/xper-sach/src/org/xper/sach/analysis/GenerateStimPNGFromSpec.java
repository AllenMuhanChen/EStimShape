package org.xper.sach.analysis;

import java.awt.image.BufferedImage;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.FloatBuffer;
import java.nio.IntBuffer;

//import myMathLib.MyMath;

import org.lwjgl.BufferUtils;
import org.lwjgl.LWJGLException;
import org.lwjgl.Sys;
import org.lwjgl.opengl.Display;
import org.lwjgl.opengl.DisplayMode;
import org.lwjgl.opengl.EXTTextureFilterAnisotropic;
import org.lwjgl.opengl.GL11;
import org.lwjgl.util.glu.GLU;
import org.lwjgl.util.glu.MipMap;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.sach.drawing.stimuli.BsplineObjectSpec;


public class GenerateStimPNGFromSpec {

	
// Display parameters:	
private int WINDOW_WIDTH  = 400;
private int WINDOW_HEIGHT = 300; 	
	
private String WINDOW_TITLE  = "";	
private int WINDOW_XLOCATION = 0;
private int WINDOW_YLOCATION = 0; 
	
	

//Light material properties:
//Material (front/back)
private static float[] mat_ambient_front  = {0.2f, 0.2f, 0.2f, 1.0f};
private static float[] mat_specular_front = {0.0f, 0.0f, 0.0f, 1.0f};  // Highlight 
private static float[] mat_diffuse_front  = {0.8f, 0.8f, 0.8f, 1.0f};
private static float mat_shininess_front  = 0.00f; // (range 0 to 128) . // Shininess of highlights

private static float[] mat_ambient_back  = {0.0f, 0.0f, 0.0f, 1.0f};
private static float[] mat_specular_back = {0.0f, 0.0f, 0.0f, 1.0f};  // Highlight 
private static float[] mat_diffuse_back  = {0.0f, 0.0f, 0.0f, 1.0f};
private static float mat_shininess_back  = 0.00f; // (range 0 to 128) . // Shininess of highlights

//Lighting:
private static float[] diffuse_light  = {0.8f, 0.8f, 0.8f, 1.0f};
private static float[] specular_light = {0.0f, 0.0f, 0.0f, 1.0f}; // Always make it the same as diffuse
private static float[] ambient_light  = {0.8f, 0.8f, 0.8f, 1.0f};

private static float[] globalAmbientLight = {0.0f,0.0f,0.0f,1.0f};
private static boolean twoSidedLighting   = false; // If this is true it calculates normals for the back surface as well.
	
private static boolean useAttenuation = false;
private static float constAtt = 1.0f;
private static float linAtt  = 0.00015f;
private static float quadAtt = 0.0f;

//Light source:
private float[] lightSourcePos = new float[4];

public boolean cullSurface = true;
public boolean doFog= false;



//Knot-vectors and NURBS stuff:
//NURBS params:
//public NURBS_JNI NURBS_OBJ = new NURBS_JNI();
//public ByteBuffer handle = NURBS_OBJ.nCreate();
//public ByteBuffer handleObjContext = NURBS_OBJ.nCreate();

//Creating buffer object:
//We create a direct byte buffer of size that equals the total number of control point x 4Bytes. (x 4bytes since each ctrl.pt will be stored as a float).
public ByteBuffer bufferArrayCtrlPts;

//Knot Vectors
public ByteBuffer UKnots;
public ByteBuffer VKnots;

public int numberOfUKnots;
public int numberOfVKnots;

public int NumUCtrlPts;
public int NumVCtrlPts;


public ByteBuffer bufferArrayCtrlPtsContextObj;

public ByteBuffer UKnotsContextObj;
public ByteBuffer VKnotsContextObj;

public int numberOfUKnotsContextObj;
public int numberOfVKnotsContextObj;

public int NumUCtrlPtsContextObj;
public int NumVCtrlPtsContextObj;



//Texture:

//Hexagonal:
public static int[] hexTextureRes = {25,40,70,95};
public static int[] hexTexResolution = {2048,2048,4096,4096};
public static int numHexTextureObjs = 4;
public static IntBuffer texNameHex = BufferUtils.createIntBuffer(numHexTextureObjs);


// Texture type:
public static int[] cicleTextureRes = {50}; // Percent dots
public static int[] circleTexResolutionPostHoc = {2048};
public static int numCircleTextureObjs = 1;
public static IntBuffer texNameCircles = BufferUtils.createIntBuffer(numCircleTextureObjs);

//Hexagonal post-hoc texture resolution
//public static int[] hexTextureResPostHoc = {10,70,40,120};
//public static int[] hexTexResolutionPostHoc = {2048,2048,4096,4096};
//public static int numHexTextureObjsPostHoc = 4;
//public static IntBuffer texNameHexPostHoc = BufferUtils.createIntBuffer(numHexTextureObjsPostHoc);
/*
//Perspective texture:
public static int[] perspTextureRes = {100};//{50,100,200}; // Number of lines in the U and V dimension
public static int numPerspTextureObjs = 1;
public static IntBuffer texNamePersp = BufferUtils.createIntBuffer(numPerspTextureObjs);
*/


//Dot texture
public static int[] dotsTextureRes = {5}; //{2,5,10}; // Percent dots
public static int numDotsTextureObjs = 1;
public static IntBuffer texNameDots = BufferUtils.createIntBuffer(numDotsTextureObjs);

public static boolean doAnisotropicFilter = false;




public static int[] nonGradHexRes =  {12,30};
public static int totalNumHexagonsLowRes;
public static float[][] xCoordHexLowRes;
public static float[][] yCoordHexLowRes;

public static int totalNumHexagonsHighRes;
public static float[][] xCoordHexHighRes;
public static float[][] yCoordHexHighRes;


public static int numPointsPerLine = 20;
public static int[] nonGradBezRes =  {12,24};
public static int totalNumLinesBezLowRes;
public static float[][] xCoordBezLowRes;
public static float[][] yCoordBezLowRes;

public static int totalNumLinesBezHighRes;
public static float[][] xCoordBezHighRes;
public static float[][] yCoordBezHighRes;


public static boolean alreadyPerformedQuickPostHoc = false;


//public static int numNaturalImgs = LandscapeRenderer.numNaturalImgs;
//public static IntBuffer naturalImgTexName = BufferUtils.createIntBuffer(numNaturalImgs);

public BsplineObjectSpec spec;

public AbstractRenderer rendererUtil;

public GenerateStimPNGFromSpec(AbstractRenderer renderer){
	rendererUtil = renderer;
	
	try{
		initDisplay();
	}
	catch(LWJGLException ex){
		System.out.println(ex.toString());
	}
	
	long tt1,tt2;
	tt1 = System.currentTimeMillis();
	initGLParams();
	tt2 = System.currentTimeMillis();
	System.out.println("Setting up initGLParams() GenerateStimPNGFromSpec: " + (tt2 - tt1));
}
	
	
private void initDisplay() throws LWJGLException {	
	DisplayMode m;
	
    m = new DisplayMode(WINDOW_WIDTH, WINDOW_HEIGHT);
	
	Display.setDisplayMode(m);	 
	Display.setTitle(WINDOW_TITLE);

	Display.create();
	Display.setLocation(WINDOW_XLOCATION, WINDOW_YLOCATION);
	Display.makeCurrent();
}		
	
// Initialize openGL: viewing, projection, lighting and material properties.
public void initCamera(boolean usedStereoSetup) {
	
	double tmp;
		
	//double yComp,xComp;	

	// Initialize view-box parameters:
	double near_plane_depth  = rendererUtil.getDistance(); // mm
	double depth 			 = rendererUtil.getDepth(); //mm This is the distance behind the near plane.
	double far_plane_depth  = near_plane_depth + depth; // This is the far-plane depth of the view box.
	double cameraPosOnZAxis = near_plane_depth; // This puts the near-plane at the z = 0 depth.
	double interOcularDistance  = rendererUtil.getPupilDistance();

	double heightOfNearPlane = rendererUtil.getHeight();
	double widthOfNearPlane;
	
	//if(usedStereoSetup)
	widthOfNearPlane  = rendererUtil.getWidth()/2.0;
	//else
	//	widthOfNearPlane  = rendererUtil.getWidth();	

	// double aspect_ratio = widthOfNearPlane/heightOfNearPlane;

	double minNearX = -widthOfNearPlane/2.0;
	double maxNearX =  widthOfNearPlane/2.0;

	double minNearY = -heightOfNearPlane/2.0;
	double maxNearY =  heightOfNearPlane/2.0;

	
	//field_of_view = 2.0*Math.atan2(maxNearY,near_plane_depth)*(180/Math.PI);
	//inStereo = useStereo;

	double[] CAMERA_POS = new double[3];
	double effectiveNearPlaneDist=0.0;
	double effectiveFarPlaneDist=0.0;
	if(usedStereoSetup){
		// tmp is the amount the viewpoint needs to be shifted in front of (more negative z)
		// the original camera position (cameraPosOnZAxis)
			tmp = near_plane_depth/(1+(widthOfNearPlane/interOcularDistance));
			double effectiveCameraPosOnZAxisStereo = cameraPosOnZAxis - tmp;
		
			CAMERA_POS[0] = 0.0;
			CAMERA_POS[1] = 0.0;
			CAMERA_POS[2] = effectiveCameraPosOnZAxisStereo;
			
			effectiveNearPlaneDist = effectiveCameraPosOnZAxisStereo;
			effectiveFarPlaneDist  = effectiveNearPlaneDist  + depth;
			
			/*
			field_of_viewStereo    = 2.0*Math.atan2(maxNearY, effectiveCameraPosOnZAxisStereo)*(180/Math.PI); // Make it degrees
			maxFarY = (effectiveCameraPosOnZAxisStereo+depth)*Math.tan((field_of_viewStereo/2)*Math.PI/180);
			minFarY = -maxFarY;
			maxFarX =  maxFarY*aspect_ratio; // aspect_ratio = width/height
			minFarX = -maxFarX;
			*/
		}
		else{
			
			CAMERA_POS[0] = 0.0;
			CAMERA_POS[1] = 0.0;
			CAMERA_POS[2] = cameraPosOnZAxis;
			/*
			maxFarY =  far_plane_depth*Math.tan((field_of_view/2)*Math.PI/180);
			minFarY = -maxFarY;
			
			maxFarX =  maxFarY*aspect_ratio;
			minFarX = -minFarX;	
			*/
		}
		
	
    // Setting viewing transformation:
    // 1st we load the model-view matrix as our current transformation matrix
    // and then set it to the identity matrix. These 2 steps are redundant since
    // the current matrix is the model-view by default and set to identity at the start.
    GL11.glMatrixMode(GL11.GL_MODELVIEW);
    GL11.glLoadIdentity();
    
    // The default position of the camera is at the origin pointing down the negative
    // z-axis. Its up direction is the positive y-axis.
    //             eyeX,          		 eyeY,         		   eyeZ,            centerX,centerY,centerZ, upX, upY, upZ   
    GLU.gluLookAt((float)CAMERA_POS[0], (float)CAMERA_POS[1], (float)CAMERA_POS[2], 0.0f, 0.0f,-1.0f, 0.0f, 1.0f, 0.0f);
         

    GL11.glMatrixMode(GL11.GL_PROJECTION);
    GL11.glLoadIdentity();
    
    if(usedStereoSetup)
    	GL11.glFrustum((float)minNearX, (float)maxNearX, (float)minNearY, (float)maxNearY, (float)effectiveNearPlaneDist, (float)effectiveFarPlaneDist);
    else
    	GL11.glFrustum((float)minNearX, (float)maxNearX, (float)minNearY, (float)maxNearY, near_plane_depth, far_plane_depth);
    

    
    GL11.glMatrixMode(GL11.GL_MODELVIEW);


}	
	
	
private void initGLParams(){
	
	GL11.glClearColor(0.2f, 0.2f, 0.2f, 1.0f); // 'Clearing color' set to black.
	
	// Set shade-model:
	GL11.glShadeModel(GL11.GL_SMOOTH);
    
	GL11.glEnable(GL11.GL_DEPTH_TEST);    // Enables hidden-surface removal allowing for use of depth buffering
	GL11.glEnable(GL11.GL_AUTO_NORMAL);   // Automatic normal generation when doing NURBS, if not enabled we have to provide the normals ourselves if we want to have a lighted image (which we do).
	  	
// GL11.glEnable(GL11.GL_BLEND); 
// GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
	
	
	setLightMaterialProperties();
	
	// texture related:
	String fileNameTexture;
	int totalNumBytesInTexture = (4096)*(4096)*4;
	byte[] temp;

	// Hexagonal texture:
	GL11.glGenTextures(texNameHex);
	for(int i=0;i<numHexTextureObjs;i++){
		
		totalNumBytesInTexture = hexTexResolution[i]* hexTexResolution[i]*4;
		
		//fileNameTexture = "/mnt/data/home/m2_sia/workspace/xper-sia-fix-chg-example/textureFiles/Dots" + resolutionHeight + "by" + resolutionWidth;
		//fileNameTexture = "/mnt/data/home/m2_sia/workspace/xper-sia-fix-chg-example/textureFiles/Perspective" + resolutionHeight + "by" + resolutionWidth;
		fileNameTexture = "/mnt/data/home/r2_sia/workspace/xper-sia-fix-chg-example/textureFiles/HexagonalTexture" + hexTexResolution[i] + "_" + hexTextureRes[i];

		temp = new byte[totalNumBytesInTexture];
		int tmpNumBytesRead=totalNumBytesInTexture;

		try{
		    FileInputStream fin = new FileInputStream(fileNameTexture);
		    tmpNumBytesRead = fin.read(temp);
		    fin.close();
		}
		catch(FileNotFoundException exception){
			System.out.println("Did not find texture file: " + exception);	
		}
		catch(IOException ee){
			 System.out.println ( "IO Exception =: " + ee );	
		}

		if(tmpNumBytesRead!=totalNumBytesInTexture){
			System.err.println("Did not read all texel Bytes");
			System.exit(-1);
			//throw new OutOfRangeException("Did not read all texel Bytes");
		}
		
		
		ByteBuffer checkImageBuffer = (ByteBuffer) BufferUtils.createByteBuffer(temp.length).put(temp).flip();
		GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT, 1);

		
		   
		GL11.glBindTexture(GL11.GL_TEXTURE_2D, texNameHex.get(i));

		MipMap.gluBuild2DMipmaps(GL11.GL_TEXTURE_2D, GL11.GL_RGBA, hexTexResolution[i], hexTexResolution[i],GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, checkImageBuffer);
		
		GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_S, GL11.GL_CLAMP);//GL_REPEAT GL_CLAMP
		GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_T, GL11.GL_CLAMP);

		//GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_LINEAR); // GL_LINEAR, GL_NEAREST
		//GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_LINEAR);

		GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_LINEAR); // GL_LINEAR, GL_NEAREST
		GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_LINEAR_MIPMAP_LINEAR);

		GL11.glTexEnvf(GL11.GL_TEXTURE_ENV, GL11.GL_TEXTURE_ENV_MODE, GL11.GL_MODULATE); // GL11.GL_MODULATE
		

		// FloatBuffer max_a = BufferUtils.createFloatBuffer(1);
		// max_a.put(EXTTextureFilterAnisotropic.GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT).flip(); 
		// Due to LWJGL buffer check, you can't use smaller sized buffers (min_size = 16 for glGetFloat()).
		final FloatBuffer max_a = BufferUtils.createFloatBuffer(16);
		max_a.rewind();

		  // Grab the maximum anisotropic filter.
		GL11.glGetFloat(EXTTextureFilterAnisotropic.GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT, max_a);


		// float testT = max_a.get(0);

		  // Grab the maximum anisotropic filter.
		// GL11.glGetFloat(EXTTextureFilterAnisotropic.GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT, max_a);


		 //Do anisotropic filtering:
		 if(doAnisotropicFilter)
			GL11.glTexParameterf(GL11.GL_TEXTURE_2D, EXTTextureFilterAnisotropic.GL_TEXTURE_MAX_ANISOTROPY_EXT, max_a.get(0));

	
	
	}
	
}	



public static void setLightMaterialProperties(){
	
	GL11.glEnable(GL11.GL_LIGHT0);
	
	// Diffuse (light coming from a specific direction. For example sun light coming from above). It looks equally bright from all directions, since it reflects in all directions upon impact.
	FloatBuffer diffuselightBuffer = BufferUtils.createFloatBuffer(diffuse_light.length);
	diffuselightBuffer.put(diffuse_light).flip(); 	
	GL11.glLight(GL11.GL_LIGHT0, GL11.GL_DIFFUSE, diffuselightBuffer);
		  	
	// We may want to turn off specular (reflects shininess light for non-object stimuli.  Set its value to {0,0,0,1}
	FloatBuffer specularlightBuffer = BufferUtils.createFloatBuffer(specular_light.length);
	specularlightBuffer.put(specular_light).flip(); 	
	GL11.glLight(GL11.GL_LIGHT0, GL11.GL_SPECULAR, specularlightBuffer);
		  	
	// Specifically for interiors we may want to have an ambient component.
	FloatBuffer ambientlightBuffer = BufferUtils.createFloatBuffer(ambient_light.length);
	ambientlightBuffer.put(ambient_light).flip(); 	
	GL11.glLight(GL11.GL_LIGHT0, GL11.GL_AMBIENT, ambientlightBuffer);
		  	
		  	
	// Lighting model properties:
	// Whether to have 2 sided lighting. Important if we want to have the inside of a shape
	// appear visible. 2 sided lighting is time-consuming so we could turn it on only when we have
	// an interior stimulus.
	if(twoSidedLighting)
		GL11.glLightModeli(GL11.GL_LIGHT_MODEL_TWO_SIDE,GL11.GL_TRUE);
		  	
	FloatBuffer globalLightBuffer = BufferUtils.createFloatBuffer(globalAmbientLight.length);
	globalLightBuffer.put(globalAmbientLight).flip(); 	
	GL11.glLightModel(GL11.GL_LIGHT_MODEL_AMBIENT, globalLightBuffer);
		  	
		  	
		  	 //GL11.glLightModeli(GL11.GL_LIGHT_MODEL_LOCAL_VIEWER,GL11.GL_TRUE);
		    
		    ////////////////////////////////// Material properties //////////////////////////////////////////////
		    // Material properties:
		    // Again ambient, specular and diffuse components (% of the light that is reflected)
		    // The properties can be applied separately to front and back surface.
		    // PG 203 of red-book has a good description of the different material components.
		  
		    FloatBuffer mat_ambientBuffer_Front;
		    FloatBuffer mat_specularBuffer_Front;
		    FloatBuffer mat_diffuseBuffer_Front;
		   
			// Ambient:
			mat_ambientBuffer_Front = BufferUtils.createFloatBuffer(mat_ambient_front.length);
			mat_ambientBuffer_Front.put(mat_ambient_front).flip();
			GL11.glMaterial(GL11.GL_FRONT, GL11.GL_AMBIENT, mat_ambientBuffer_Front);
				 
			// specular
			mat_specularBuffer_Front = BufferUtils.createFloatBuffer(mat_specular_front.length);
			mat_specularBuffer_Front.put(mat_specular_front).flip();
			GL11.glMaterial(GL11.GL_FRONT, GL11.GL_SPECULAR, mat_specularBuffer_Front);
			
			// Diffuse (Most important).
			mat_diffuseBuffer_Front = BufferUtils.createFloatBuffer(mat_diffuse_front.length);
			mat_diffuseBuffer_Front.put(mat_diffuse_front).flip();
			GL11.glMaterial(GL11.GL_FRONT, GL11.GL_DIFFUSE, mat_diffuseBuffer_Front);
			
			GL11.glMaterialf(GL11.GL_FRONT, GL11.GL_SHININESS, mat_shininess_front);
			
			
			if(twoSidedLighting){
			    FloatBuffer mat_ambientBuffer_Back;
			    FloatBuffer mat_specularBuffer_Back;
			    FloatBuffer mat_diffuseBuffer_Back;
				
				mat_ambientBuffer_Back = BufferUtils.createFloatBuffer(mat_ambient_back.length);
				mat_ambientBuffer_Back.put(mat_ambient_back).flip();
				GL11.glMaterial(GL11.GL_BACK, GL11.GL_AMBIENT, mat_ambientBuffer_Back);
				
				mat_specularBuffer_Back = BufferUtils.createFloatBuffer(mat_specular_back.length);
			    mat_specularBuffer_Back.put(mat_specular_back).flip();
				GL11.glMaterial(GL11.GL_BACK, GL11.GL_SPECULAR, mat_specularBuffer_Back);
				
				// Diffuse (Most important).
				mat_diffuseBuffer_Back = BufferUtils.createFloatBuffer(mat_diffuse_back.length);
				mat_diffuseBuffer_Back.put(mat_diffuse_back).flip();
				GL11.glMaterial(GL11.GL_BACK, GL11.GL_DIFFUSE, mat_diffuseBuffer_Back);
				 
				GL11.glMaterialf(GL11.GL_BACK, GL11.GL_SHININESS, mat_shininess_back);	 				 
			}
			
			
			
			if(useAttenuation){
				//FloatBuffer constAttenuation = BufferUtils.createFloatBuffer(1);
				//constAttenuation.put(constAtt).flip();
			  	//GL11.glLight(GL11.GL_LIGHT0, GL11.GL_CONSTANT_ATTENUATION, constAttenuation);
			  	GL11.glLightf(GL11.GL_LIGHT0, GL11.GL_CONSTANT_ATTENUATION, constAtt);
			  	
			 // 	FloatBuffer linAttenuation = BufferUtils.createFloatBuffer(1);
			  	//linAttenuation.put(linAtt).flip();
			  	//GL11.glLight(GL11.GL_LIGHT0, GL11.GL_LINEAR_ATTENUATION,linAttenuation );
			  	GL11.glLightf(GL11.GL_LIGHT0, GL11.GL_LINEAR_ATTENUATION,linAtt);
			  	
			  	GL11.glLightf(GL11.GL_LIGHT0, GL11.GL_QUADRATIC_ATTENUATION,quadAtt);
			  
			}
	
	}


public void setLightPos(){
	
	for(int i=0;i<4;i++){
//		lightSourcePos[i] = spec.landParams.lightSourcePos[i];
	}
	
	FloatBuffer light_positionBuffer = BufferUtils.createFloatBuffer(lightSourcePos.length);        
	light_positionBuffer.put(lightSourcePos).flip();
	GL11.glLight(GL11.GL_LIGHT0, GL11.GL_POSITION, light_positionBuffer);
	
}


public void savePNGshapeSpec(BsplineObjectSpec inpSpec,String fileName){
	
	// Clearing the color and depth buffers
	GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT);
	
	//Display.setTitle(String.valueOf(inpSpec.avgSpikeRate));
	
	// Add spike info to file name:
	String tmpAvgSpikeRate = null;
//	tmpAvgSpikeRate = String.valueOf(inpSpec.avgSpikeRate);
	if(tmpAvgSpikeRate.length()>5)
		tmpAvgSpikeRate = tmpAvgSpikeRate.substring(0, 5);
	
	String tmpStdSpike = null;
//	tmpStdSpike = String.valueOf(inpSpec.getSampleSTDev());
	if(tmpStdSpike.length()>4)
		tmpStdSpike = tmpStdSpike.substring(0, 4);
	
//	if(inpSpec.isBlankStim()){
//		//fileName = fileName + " " + Math.rint(inpSpec.avgSpikeRate) + " std: " + Math.rint(inpSpec.getSampleSTDev());
//		fileName = fileName + " " +  tmpAvgSpikeRate + " std: " + tmpStdSpike;//   Math.rint(inpSpec.getSampleSTDev());
//	}
	else{
		//fileName = fileName + " " + Math.rint(inpSpec.avgSpikeRate - inpSpec.correspondingBlankAvgRate) + " std: " + Math.rint(inpSpec.getSampleSTDev()) + " Fix: " + inpSpec.landParams.fixDiscreteIndex;
//		fileName = fileName + " " + tmpAvgSpikeRate + " std: " + tmpStdSpike + " Fix: " + inpSpec.landParams.fixDiscreteIndex;
	}
	spec = inpSpec;
	
	initCamera(false);
	
//	if(spec.isShapeBlank){
//		setLightPos();
//		GL11.glDisable(GL11.GL_LIGHTING);
//		
//		GL11.glPointSize((float)2.0);
//		GL11.glColor3f((float)1.0, (float)0.0, (float)0.0);
//		GL11.glBegin(GL11.GL_POINTS);
//			GL11.glVertex3f((float)0.0, (float)0.0, (float)0.0);
//			GL11.glVertex3f((float)spec.landParams.fixationDisparity, (float)0.0, (float)0.0);
//	
//		GL11.glEnd();
//	
//		
//		GL11.glEnable(GL11.GL_LIGHTING);
//		//System.out.println("Empty task");
//		
//		saveImage(fileName);
//		return;
//	}
	


	
	// Draw shape:

	GL11.glHint(GL11.GL_PERSPECTIVE_CORRECTION_HINT,GL11.GL_NICEST);
	//GL11.glHint(GL11.GL_LINE_SMOOTH_HINT,GL11.GL_DONT_CARE);
	//GL11.glHint(GL11.GL_POLYGON_SMOOTH_HINT,GL11.GL_DONT_CARE);
	
	
	// Clearing the color and depth buffers:
	// GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT);

	// Culling and reversing polygon facing:
	if(cullSurface){
	    GL11.glCullFace(GL11.GL_BACK);
	    GL11.glEnable(GL11.GL_CULL_FACE);
	}

	
	if(doFog){
		GL11.glEnable(GL11.GL_FOG);
		//GL11.glFogi(GL11.GL_FOG_MODE, GL11.GL_EXP);
		//GL11.glHint(GL11.GL_FOG_HINT,GL11.GL_NICEST);
	}
	else{
		GL11.glDisable(GL11.GL_FOG);
	}
	

	setLightPos();
	
	
	long t1,t2;
	t1 = System.currentTimeMillis();
	
//	if(spec.haveShading){
//		// Turn on light:
//		GL11.glEnable(GL11.GL_LIGHTING);
//	}
//	else{
		GL11.glDisable(GL11.GL_LIGHTING);
		GL11.glColor3f(0.52f, 0.52f, 0.52f);
//	}

	
	
	
	GL11.glDisable(GL11.GL_LIGHTING);
	//GL11.glDisable(GL11.GL_LIGHT0);	
	t2 = System.currentTimeMillis();
	System.out.println("Time taken to render shape: " + (t2-t1));
	System.out.println("NumUCtrlPts " + NumUCtrlPts);
	System.out.println("NumVCtrlPts " + NumVCtrlPts);
	
	
	// Draw fixation:
	GL11.glDisable(GL11.GL_LIGHTING);
	GL11.glDisable(GL11.GL_TEXTURE_2D);	
	
	GL11.glPointSize((float)1.0);
	GL11.glColor3f((float)1.0, (float)0.0, (float)0.0);
	GL11.glBegin(GL11.GL_POINTS);
		GL11.glVertex3f((float)0.0, (float)0.0, (float)0.0);
//		if(spec.stereo)
//			GL11.glVertex3f((float)spec.landParams.fixationDisparity, (float)0.0, (float)0.0);
//		else
			GL11.glVertex3f((float)0.0, (float)0.0, (float)0.0);
	GL11.glEnd();
	

	// Save file:
	saveImage(fileName);
	
	Display.update();
	
}


public void saveImage(String saveFilename){
	 ByteBuffer framebytes = allocBytes(WINDOW_WIDTH * WINDOW_HEIGHT * 3);
//		ByteBuffer framebytes = new ByteBuffer();
		//final int SIZE_BYTE = 4;
		//framebytes.allocateDirect( width*height*3 * SIZE_BYTE).order(ByteOrder.nativeOrder());



	     int[] pixels = new int[WINDOW_WIDTH * WINDOW_HEIGHT];
	     int bindex;
	     // grab a copy of the current frame contents as RGB (has to be UNSIGNED_BYTE or colors come out too dark)
	     GL11.glReadPixels(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, GL11.GL_RGB, GL11.GL_UNSIGNED_BYTE, framebytes);
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
//	     pixels = GLImage.flipPixels(pixels, WINDOW_WIDTH, WINDOW_HEIGHT);
	     
	     try {
	     	//ByteArrayOutputStream out = new ByteArrayOutputStream();
	         // Create a BufferedImage with the RGB pixels then save as PNG
	         BufferedImage image = new BufferedImage(WINDOW_WIDTH, WINDOW_HEIGHT, BufferedImage.TYPE_INT_ARGB);
	         image.setRGB(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, pixels, 0, WINDOW_WIDTH);

	         javax.imageio.ImageIO.write(image, "png", new File(saveFilename));

//	          ImageIO.write(image, "png", out);
//	          byte[] data = out.toByteArray();
	//
//		System.out.println("the data length is " + data.length);
	//
//		    File outFile = new File("./nowScShot.png");
//	 	    BufferedOutputStream bos = new BufferedOutputStream(new FileOutputStream(outFile));             
	//
//	              bos.write(data, 0, data.length);			         
//	    		bos.flush();
//	    		bos.close();
			// we should write the Data into a file
	         //dbUtil.writeThumbnail(stimId,data);
	         
	     }
	     catch (Exception e) {
	         System.out.println("screenShot(): exception " + e);
	     }
	
	
}

public static ByteBuffer allocBytes(int howmany) {
	final int SIZE_BYTE = 4;
     return ByteBuffer.allocateDirect(howmany * SIZE_BYTE).order(ByteOrder.nativeOrder());
 }


}
