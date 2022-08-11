package org.xper.sach.drawing.stick;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.FloatBuffer;
import java.util.ArrayList;
import java.util.List;

import org.lwjgl.BufferUtils;
import org.lwjgl.LWJGLException;
import org.lwjgl.opengl.ARBFragmentShader;
import org.lwjgl.opengl.ARBShaderObjects;
import org.lwjgl.opengl.ARBVertexShader;
import org.lwjgl.opengl.Display;
import org.lwjgl.opengl.DisplayMode;
import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.GL20;
import org.lwjgl.util.glu.GLU;

import org.xper.drawing.Context;
import org.xper.drawing.RGBColor;

import org.xper.sach.drawing.splines.MyPoint;
import org.xper.sach.drawing.stick.mathLib.stickMath_lib;
import org.xper.sach.drawing.stimuli.Aperture;
import org.xper.sach.drawing.stimuli.Occluder;
import org.xper.sach.drawing.stimuli.ShapeMiscParams;
import org.xper.sach.drawing.stimuli.TextureType;

public class Testing3dMA {	
	MStickSpec msSpec;
	
	ShapeMiscParams shapeParams = new ShapeMiscParams();
	List<Aperture> apertures = new ArrayList<Aperture>();
	Occluder occluder;
	String stimType = "GA";
	
	MatchStick msShape = new MatchStick();
	
	float occluderAlpha = 1f;
	
	int shaderProgram = 0;
	
	public static void main(String[] args) throws LWJGLException {
		try {
			Testing3dMA testWindow = new Testing3dMA();	
			
			testWindow.initDisplay();
			testWindow.init();
			testWindow.generateShape();
			try {
			testWindow.render(TextureType.SHADE);
			Thread.sleep(5500);
			testWindow.render(TextureType.DOTS);
			Thread.sleep(5500);
			testWindow.render(TextureType.TWOD);
			Thread.sleep(5500);
			} catch (InterruptedException ex) {
				
			}
			
			
//			for (int i=1; i<3; i++) {
//				try {
//				Thread.sleep(5500);
//				} catch (InterruptedException ex) {
//					
//				}
//				// testWindow.msShape.mutate(stickMath_lib.randInt(1, 8));
//				testWindow.morphShape();
//				testWindow.render();
//			}
			
		} catch (LWJGLException ex) {
            System.out.println(ex.toString());
		} finally {
			Display.destroy();
        }
	}
	
    protected void initDisplay() throws LWJGLException {
        // Set display mode.
        // DisplayMode[] modes = Display.getAvailableDisplayModes();

        DisplayMode m = new DisplayMode(800, 800);
        Display.setDisplayMode(m);

        // Set various properties.
        Display.setTitle("Window Title");
        Display.setFullscreen(false);
        Display.setVSyncEnabled(false);

        Display.create();
        Display.setLocation(200, 100);
        Display.makeCurrent();
    }

    protected void init() {
        GL11.glClearColor(0.3f, 0.3f, 0.3f, 1.0f);
        
        GL11.glShadeModel(GL11.GL_SMOOTH);
        GL11.glEnable(GL11.GL_DEPTH_TEST);    // Enables hidden-surface removal allowing for use of depth buffering
		GL11.glEnable(GL11.GL_AUTO_NORMAL);   // Automatic normal generation when doing NURBS, if not enabled we have to provide the normals ourselves if we want to have a lighted image (which we do).
        
        GL11.glMatrixMode(GL11.GL_PROJECTION);
        GL11.glLoadIdentity();

        GLU.gluPerspective(45.0f, (float)500.0/(float)500.0, 0.01f, 100.0f);
        GL11.glMatrixMode(GL11.GL_MODELVIEW);
        GL11.glLoadIdentity();

        GLU.gluLookAt(0.0f, 0.0f, 7.0f, 0.0f, 0.0f, 0.0f, 0.0f, 1.0f, 0.0f);
        // gluLookAt (eyeX,eyeY,eyeZ, centerX,centerY, centerZ, UpX, upY, upZ)
        
        GL11.glScalef(0.025f, 0.025f, 0.025f);
        //GL11.glTranslatef( 0.0f, 0.0f, -10.0f);

        this.initLight();

        GL11.glDisable (GL11.GL_BLEND);
        GL11.glDisable (GL11.GL_POLYGON_SMOOTH);
        GL11.glEnable (GL11.GL_DEPTH_TEST);
        
    }
    
    protected void initLight()
    {
        float mat_shininess = .3f;
        float[] mat_ambient = { 0.0f, 0.0f, 0.0f, 1.0f};
        float[] mat_specular = {.2f, .2f, .2f, 1.0f};
        float[] mat_diffuse = {0.008f, 0.008f, 0.008f,  1.0f };

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

        // make sure white light
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

        GL11.glEnable(GL11.GL_AUTO_NORMAL);
    }

    protected void generateShape() {
    	
    	msShape.genMatchStickRand();
        msSpec = new MStickSpec();
        msSpec.setMStickInfo(msShape);
        msSpec.vertex = null;
//        String specString = msSpec.toXml();
        // save this specString

        // MORPH
        // get the specString
//        msSpec = MStickSpec.fromXml(specString);
//        msShape.genMatchStickFromShapeSpec(msSpec);
//        msShape.mutate(stickMath_lib.randInt(1, 8));
//        msSpec = new MStickSpec();
//        msSpec.setMStickInfo(msShape);
//        msSpec.vertex = null;
//        String specString = msSpec.toXml();
        // save this specString
    }
    
    protected void morphShape() {
    	
    	msShape.mutate(stickMath_lib.randInt(1, 8));
        msSpec = new MStickSpec();
        msSpec.setMStickInfo(msShape);
        msSpec.vertex = null;
//        String specString = msSpec.toXml();
        // save this specString
    }

    protected void render(TextureType tt) {
        GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT);

        RGBColor color = new RGBColor(1,1,1);
        msShape.drawSkeleton(tt, color,"","");
        
        GL11.glFlush();
        
        Display.update();
    }
    
    void makeStencil(Context context, int index) {
		GL11.glClear(GL11.GL_STENCIL_BUFFER_BIT);
		GL11.glColorMask(false,false,false,false);
		
		GL11.glEnable(GL11.GL_STENCIL_TEST);
		GL11.glStencilFunc(GL11.GL_ALWAYS, 1, 1);
		GL11.glStencilOp(GL11.GL_KEEP, GL11.GL_KEEP, GL11.GL_REPLACE);
		
		GL11.glDisable(GL11.GL_DEPTH_TEST);
		
		drawAperture(context,index);
		
		GL11.glEnable(GL11.GL_DEPTH_TEST);
		GL11.glColorMask(true, true, true, true);
		GL11.glStencilFunc(GL11.GL_EQUAL, 1, 1);
		GL11.glStencilOp(GL11.GL_KEEP, GL11.GL_KEEP, GL11.GL_KEEP);
		
		GL11.glPushMatrix();
			drawShape(context,0);
		GL11.glPopMatrix();

		GL11.glDisable(GL11.GL_STENCIL_TEST);  		
	}
	
	void drawAperture(Context context, int index) {		
		double theta, x, y; 
		GL11.glBegin(GL11.GL_TRIANGLE_FAN);
	    for(int ii = 0; ii < 200; ii++)
	    {
	        theta = 2.0f * 3.1415926f * ii / 200;
	        x = apertures.get(index).getS() * Math.cos(theta);//calculate the x component
	        y = apertures.get(index).getS() * Math.sin(theta);//calculate the y component
	        GL11.glVertex2d(x + apertures.get(index).getX(), y + apertures.get(index).getY());
	    }
	    GL11.glEnd();
	}
	
	// draw the shape
	void drawShape(Context context, int index) {
		GL11.glColor3f(shapeParams.getColor().getRed(),
				shapeParams.getColor().getGreen(),
				shapeParams.getColor().getBlue());
		
		GL11.glPolygonMode(GL11.GL_FRONT_AND_BACK,GL11.GL_FILL);
		GL11.glEnable(GL11.GL_POLYGON_SMOOTH);
		GL11.glHint(GL11.GL_POLYGON_SMOOTH_HINT, GL11.GL_NICEST);
		GL11.glEnable(GL11.GL_LINE_SMOOTH);
		GL11.glHint(GL11.GL_LINE_SMOOTH_HINT, GL11.GL_NICEST);
		
		GL11.glEnable(GL11.GL_BLEND);
		GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);

		GL11.glEnable(GL11.GL_DEPTH_TEST);
		
		msShape.drawSkeleton(shapeParams.getTextureType(),shapeParams.getColor(),"","");
		
		
		GL11.glDisable(GL11.GL_DEPTH_TEST);
		GL11.glDisable(GL11.GL_BLEND);
	}
	
	// occluder and related shader
    void drawOccluder(Context context) {

    	MyPoint lb = occluder.getLeftBottom();
    	MyPoint rt = occluder.getRightTop();
    	
        int width = (int)(Math.abs(lb.x - rt.x));
        int height = (int)(Math.abs(lb.y - rt.y));

        MyPoint center = new MyPoint((lb.x + rt.x)/2, (lb.y + rt.y)/2);

        float marginWidth = 10.0f;

        float[] apertureSpecs = {(float)apertures.get(0).getX(),(float)apertures.get(0).getY(),(float)apertures.get(0).getS(),
        		(float)apertures.get(1).getX(),(float)apertures.get(1).getY(),(float)apertures.get(1).getS()};
        
        FloatBuffer apertureSpecBuffer = BufferUtils.createFloatBuffer(2 * 3); // numHoles * numSpecsPerHole
        apertureSpecBuffer.put(apertureSpecs);
        apertureSpecBuffer.rewind();
        
        createShaders();
        
        //  critical ...
        GL11.glEnable(GL11.GL_BLEND);

        // It is recommended to have the GLSL shaderProgram in use before setting values
        GL20.glUseProgram(shaderProgram);
        int loc1 = GL20.glGetUniformLocation(shaderProgram, "marginWidth");
        GL20.glUniform1f(loc1, marginWidth);

        int loc2 = GL20.glGetUniformLocation(shaderProgram, "top");
        GL20.glUniform1f(loc2, (float)center.y + (float) height);

        int loc3 = GL20.glGetUniformLocation(shaderProgram, "bottom");
        GL20.glUniform1f(loc3, (float)center.y - (float) height);

        loc2 = GL20.glGetUniformLocation(shaderProgram, "left");
        GL20.glUniform1f(loc2, ((float)center.x - width));

        loc3 = GL20.glGetUniformLocation(shaderProgram, "right");
        GL20.glUniform1f(loc3, ((float)center.x + width ));

        loc3 = GL20.glGetUniformLocation(shaderProgram, "alphaGain");
        GL20.glUniform1f(loc3, occluderAlpha);

        loc3 = GL20.glGetUniformLocation(shaderProgram, "numHoles");
        GL20.glUniform1i(loc3, apertures.size());

        int loc4 = GL20.glGetUniformLocation(shaderProgram, "specs");
        GL20.glUniform1(loc4, apertureSpecBuffer);
        
        GL11.glBegin(GL11.GL_QUADS);
            GL11.glVertex2d(center.x - width - marginWidth, center.y - height - marginWidth);
            GL11.glVertex2d(center.x - width - marginWidth, center.y + height + marginWidth);
            GL11.glVertex2d(center.x + width + marginWidth, center.y + height + marginWidth);
            GL11.glVertex2d(center.x + width + marginWidth, center.y - height - marginWidth);
        GL11.glEnd();

        // "deactivate" the shader
        GL20.glUseProgram(0);
    }
    void createShaders(){

        int vertShader = 0, fragShader = 0;

        try {
            vertShader = createShader("screen.vert", ARBVertexShader.GL_VERTEX_SHADER_ARB);
            fragShader = createShader("screen.frag", ARBFragmentShader.GL_FRAGMENT_SHADER_ARB);
        }
        catch(Exception exc) {
            exc.printStackTrace();
            return;
        }
        finally {
            if(vertShader == 0 || fragShader == 0)
                return;
        }

        shaderProgram = ARBShaderObjects.glCreateProgramObjectARB();

        if(shaderProgram == 0)
            return;

        /*
        * if the vertex and fragment shaders setup sucessfully,
        * attach them to the shader program, link the shader program
        * (into the GL context I suppose), and validate
        */
        ARBShaderObjects.glAttachObjectARB(shaderProgram, vertShader);
        ARBShaderObjects.glAttachObjectARB(shaderProgram, fragShader);

        ARBShaderObjects.glLinkProgramARB(shaderProgram);
        if (ARBShaderObjects.glGetObjectParameteriARB(shaderProgram, ARBShaderObjects.GL_OBJECT_LINK_STATUS_ARB) == GL11.GL_FALSE) {
            System.err.println(getLogInfo(shaderProgram));
            return;
        }

        ARBShaderObjects.glValidateProgramARB(shaderProgram);
        if (ARBShaderObjects.glGetObjectParameteriARB(shaderProgram, ARBShaderObjects.GL_OBJECT_VALIDATE_STATUS_ARB) == GL11.GL_FALSE) {
            System.err.println(getLogInfo(shaderProgram));
            return;
        }
    }
    private int createShader(String filename, int shaderType) throws Exception {
        int shader = 0;
        try {
            shader = ARBShaderObjects.glCreateShaderObjectARB(shaderType);

            if(shader == 0)
                return 0;

            ARBShaderObjects.glShaderSourceARB(shader, readFileAsString(filename));
            ARBShaderObjects.glCompileShaderARB(shader);

            if (ARBShaderObjects.glGetObjectParameteriARB(shader, ARBShaderObjects.GL_OBJECT_COMPILE_STATUS_ARB) == GL11.GL_FALSE)
                throw new RuntimeException("Error creating shader: " +  getLogInfo(shader));

            return shader;
        }
        catch(Exception exc) {
            ARBShaderObjects.glDeleteObjectARB(shader);
            throw exc;
        }
    }
    private static String getLogInfo(int obj) {
        return ARBShaderObjects.glGetInfoLogARB(obj, ARBShaderObjects.glGetObjectParameteriARB(obj, ARBShaderObjects.GL_OBJECT_INFO_LOG_LENGTH_ARB));
    }
    private String readFileAsString(String filename) throws Exception {
        StringBuilder source = new StringBuilder();
        InputStream inptStrm = getClass().getResourceAsStream(filename);
        Exception exception = null;

        BufferedReader reader;
        try{
            reader = new BufferedReader(new InputStreamReader(inptStrm,"UTF-8"));

            Exception innerExc= null;
            try {
                String line;
                while((line = reader.readLine()) != null)
                    source.append(line).append('\n');
            }
            catch(Exception exc) {
                exception = exc;
            }
            finally {
                try {
                    reader.close();
                }
                catch(Exception exc) {
                    if(innerExc == null)
                        innerExc = exc;
                    else
                        exc.printStackTrace();
                }
            }

            if(innerExc != null)
                throw innerExc;
        }
        catch(Exception exc) {
            exception = exc;
        }
        finally {
            try {
            	inptStrm.close();
            }
            catch(Exception exc) {
                if(exception == null)
                    exception = exc;
                else
                    exc.printStackTrace();
            }

            if(exception != null)
                throw exception;
        }

        return source.toString();
    }
}
