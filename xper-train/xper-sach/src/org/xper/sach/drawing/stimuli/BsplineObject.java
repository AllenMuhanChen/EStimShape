package org.xper.sach.drawing.stimuli;


import java.util.ArrayList;
import java.util.List;

import javax.vecmath.Point3d;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;

import java.nio.FloatBuffer;

import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.GL20;
import org.lwjgl.opengl.ARBFragmentShader;
import org.lwjgl.opengl.ARBShaderObjects;
import org.lwjgl.opengl.ARBVertexShader;
import org.lwjgl.BufferUtils;
import org.lwjgl.LWJGLException;
import org.xper.db.vo.GenerationInfo;
import org.xper.db.vo.StimSpecEntry;

import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.Drawable;
import org.xper.drawing.RGBColor;

import org.xper.sach.analysis.PNGmaker;

import org.xper.sach.drawing.StimTestWindow;
import org.xper.sach.drawing.splines.MyPoint;
import org.xper.sach.drawing.stick.MStickSpec;
import org.xper.sach.drawing.stick.MatchStick;

import org.xper.sach.expt.SachExptSpecGenerator.StimType;
import org.xper.sach.renderer.SachPerspectiveStereoRenderer;
import org.xper.sach.util.CreateDbDataSource;
import org.xper.sach.util.Lighting;
import org.xper.sach.util.SachDbUtil;
import org.xper.sach.vo.SachTrialContext;

public class BsplineObject implements Drawable {
	BsplineObjectSpec bsospec = new BsplineObjectSpec();
	MStickSpec msSpec = new MStickSpec();
	ArrayList<Coordinates2D> texSpec;
	ArrayList<Point3d> texFaceSpec;

	MatchStick msShape = new MatchStick();
	ShapeMiscParams shapeParams = new ShapeMiscParams();
	List<Aperture> apertures = new ArrayList<Aperture>();
	Occluder occluder;
	String stimType = "GA3D";

	String descId = "";
	String folderName = "";

	float occluderAlpha = 1f;

	int shaderProgram = 0;

	boolean centerShape = false;
	boolean drawOccluder = false;
	boolean generateStickFromSpec = false;
	
	public BsplineObject() {
		super();
	}

	void createObj() {
		String stimTypeString = bsospec.getStimType();
		if (stimTypeString == null) stimTypeString = "NA";
		StimType stimType = StimType.valueOf(stimTypeString);
		if (stimType.equals(StimType.BLANK)) return;

		msShape.setExternalSize(shapeParams.size);
		msShape.setXyPos(shapeParams.pos);

		if (shapeParams.getTagForRand()) {
			generateShape();
		} else if (shapeParams.getTagForMorph()) {
			if (shapeParams.getRadiusProfile() == 0) {
				msShape.genMatchStickFromShapeSpec(msSpec);
				morphShape();
			} else {
				msShape.genMatchStickFromShapeSpec(msSpec);
				msShape.changeRadProfile(shapeParams.radiusProfile);
			}
					
		} else if (generateStickFromSpec) {
			msShape.genMatchStickFromShapeSpec(msSpec);
		}
		
		if (!centerShape)
			msShape.preloadImages(shapeParams.getTextureType(),folderName,descId);

		shapeParams.setTagForRand(false);
		shapeParams.setTagForMorph(false);
	}

	// main draw function
	public void draw(Context context) {
		StimType stimTypeEnum = StimType.valueOf(stimType);
		if (stimTypeEnum.equals(StimType.BLANK)) return;
		init();
		if (shapeParams.isOccluded) {
			drawShape(context);
			drawOccluder(context);
		} else {
			drawShape(context);
		}
	}

	// draw the shape
	void drawShape(Context context) {
		msShape.setTexSpec(texSpec);
		msShape.setTexFaceSpec(texFaceSpec);
		msShape.setDoCenterShape(centerShape);
		if (context instanceof SachTrialContext) {
			SachTrialContext c = (SachTrialContext)context;
			SachPerspectiveStereoRenderer s = (SachPerspectiveStereoRenderer)c.getRenderer();
			msShape.setScreenInverted(s.isInverted());
			msShape.setFrameNum(c.getAnimationFrameIndex());
		}
		msShape.setDoClouds(shapeParams.getDoClouds());
		msShape.setLowPass(shapeParams.getLowPass());
		msShape.setViewport(context.getViewportIndex());
		msShape.drawSkeleton(shapeParams.getTextureType(),shapeParams.getColor(),folderName,descId);
	}
	
	public void releaseAllTextures() {
		if (msShape.obj1 != null)
			msShape.obj1.releaseAllTextures();
	}

	// occluder and related shader
    void drawOccluder(Context context) {
	    	MyPoint lb = occluder.getLeftBottom();
	    	MyPoint rt = occluder.getRightTop();
//    	lb.translateBy(shapeParams.pos);
//    	rt.translateBy(shapeParams.pos);

        float width = (float)((Math.abs(lb.x - rt.x)))/2; // * shapeParams.size);
        float height = (float)((Math.abs(lb.y - rt.y)))/2; // * shapeParams.size);

        MyPoint center = new MyPoint((lb.x + rt.x)/2, (lb.y + rt.y)/2);

        float marginWidth = 10.0f;

        float s1 = (float)(apertures.get(0).getS()); // * shapeParams.size);
        float s2 = (float)(apertures.get(1).getS()); // * shapeParams.size);

        if (!apertures.get(0).getIsActive())
        	s1 = 0.0f;
        if (!apertures.get(1).getIsActive())
        	s2 = 0.0f;

        float x1 = (float)(apertures.get(0).x); // + shapeParams.getPos().x);
        float y1 = (float)(apertures.get(0).y); // + shapeParams.getPos().y);
        float x2 = (float)(apertures.get(1).x); // + shapeParams.getPos().x);
        float y2 = (float)(apertures.get(1).y); // + shapeParams.getPos().y);

//        Coordinates2D tr = SachMathUtil.cart2pol(x1, y1);
//        tr.setY(tr.getY() * shapeParams.size);
//        Coordinates2D xy = SachMathUtil.pol2cart(tr.getX(),tr.getY());
//        x1 = (float)xy.getX();
//        y1 = (float)xy.getY();
//
//        tr = SachMathUtil.cart2pol(x2, y2);
//        tr.setY(tr.getY() * shapeParams.size);
//        xy = SachMathUtil.pol2cart(tr.getX(),tr.getY());
//        x2 = (float)xy.getX();
//        y2 = (float)xy.getY();

        float[] apertureSpecs = {x1,y1,s1,x2,y2,s2};

        FloatBuffer apertureSpecBuffer = BufferUtils.createFloatBuffer(2 * 3); // numHoles * numSpecsPerHole
        apertureSpecBuffer.put(apertureSpecs);
        apertureSpecBuffer.rewind();

        createShaders();

        //  critical ...
        GL11.glEnable(GL11.GL_BLEND);
        GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);

        // It is recommended to have the GLSL shaderProgram in use before setting values
        GL20.glUseProgram(shaderProgram);
        int location = GL20.glGetUniformLocation(shaderProgram, "marginWidth");
        GL20.glUniform1f(location, marginWidth);

        location = GL20.glGetUniformLocation(shaderProgram, "top");
        GL20.glUniform1f(location, (float)center.y + (float) height);

        location = GL20.glGetUniformLocation(shaderProgram, "bottom");
        GL20.glUniform1f(location, (float)center.y - (float) height);

        location = GL20.glGetUniformLocation(shaderProgram, "left");
        GL20.glUniform1f(location, ((float)center.x - width));

        location = GL20.glGetUniformLocation(shaderProgram, "right");
        GL20.glUniform1f(location, ((float)center.x + width ));

        location = GL20.glGetUniformLocation(shaderProgram, "alphaGain");
        GL20.glUniform1f(location, occluderAlpha);

        location = GL20.glGetUniformLocation(shaderProgram, "numHoles");
        GL20.glUniform1i(location, apertures.size());

        location = GL20.glGetUniformLocation(shaderProgram, "specs");
        GL20.glUniform1(location, apertureSpecBuffer);

        GL11.glBegin(GL11.GL_QUADS);
            GL11.glVertex3d(center.x - width - marginWidth, center.y - height - marginWidth,0);
            GL11.glVertex3d(center.x - width - marginWidth, center.y + height + marginWidth,0);
            GL11.glVertex3d(center.x + width + marginWidth, center.y + height + marginWidth,0);
            GL11.glVertex3d(center.x + width + marginWidth, center.y - height - marginWidth,0);
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

    protected void generateShape() {
        // RANDGEN
    		msShape.genMatchStickRand();

        apertures.add(new Aperture());
        apertures.add(new Aperture());

        occluder = new Occluder();
    }

    protected void morphShape() {
	    	boolean success = msShape.mutate(0);
	    	if (!success)
	    		System.out.println("Mutation has gone wrong. Debug.");
    }
   
    protected void init() {
        GL11.glShadeModel(GL11.GL_SMOOTH);
        GL11.glEnable(GL11.GL_DEPTH_TEST);    // Enables hidden-surface removal allowing for use of depth buffering
		GL11.glEnable(GL11.GL_AUTO_NORMAL);   // Automatic normal generation when doing NURBS, if not enabled we have to provide the normals ourselves if we want to have a lighted image (which we do).
		GL11.glEnable(GL11.GL_POLYGON_SMOOTH);

        this.initLight();
    }
    protected void initLight()
    {
    	Lighting light = new Lighting();
    	light.setLightColor(shapeParams.color);
    	light.setTextureType(shapeParams.textureType);

        float[] mat_ambient = light.getAmbient();
        float[] mat_diffuse = light.getDiffuse();
        float[] mat_specular = light.getSpecular();
        float mat_shininess = light.getShine();

        // x: horizontal: positive right
        // y: vertical: positive up
        // z: in-out: positive out
        // w: directional or not: 1=non-directional
        float[] light_position = {(float)this.shapeParams.lightingPos.x, (float)this.shapeParams.lightingPos.y, (float)this.shapeParams.lightingPos.z, 1.0f};

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

        GL11.glLight(GL11.GL_LIGHT0, GL11.GL_POSITION, light_positionBuffer);

        // make sure white light
        float[] white_light = { 1.0f, 1.0f, 1.0f, 1.0f};
        FloatBuffer wlightBuffer = BufferUtils.createFloatBuffer( white_light.length);
        wlightBuffer.put(white_light).flip();
        GL11.glLight(GL11.GL_LIGHT0, GL11.GL_DIFFUSE, wlightBuffer);
        GL11.glLight(GL11.GL_LIGHT0, GL11.GL_SPECULAR, wlightBuffer);

        GL11.glEnable(GL11.GL_LIGHT0);
    }

	// getters and setters
	public String getStimType() {
		return stimType;
	}
	public void setStimType(String type) {
		this.stimType = type;
	}

	public MatchStick getMsShape() {
		return msShape;
	}
	public void setMsShape(MatchStick msShape) {
		this.msShape = msShape;
	}

	public RGBColor getStimForeColor() {
		return shapeParams.getColor();
	}
	public void setStimForeColor(RGBColor colo) {
		this.shapeParams.setColor(colo);
	}

	public TextureType getTextureType() {
		return shapeParams.getTextureType();
	}
	public void setTextureType(TextureType texType) {
		this.shapeParams.setTextureType(texType);
	}

	public void setSpec(String s) {
		bsospec = BsplineObjectSpec.fromXml(s);

		stimType = bsospec.getStimType();
		shapeParams = bsospec.getShapeParams();
		apertures = bsospec.getApertures();
		occluder = bsospec.getOccluder();
		
		createObj();
	}
	public BsplineObjectSpec getSpec() {
		bsospec.setStimType(stimType);
		bsospec.setShapeParams(shapeParams);
		bsospec.setApertures(apertures);
		bsospec.setOccluder(occluder);

		return bsospec;
	}

	public String getDescId() {
		return descId;
	}
	public void setDescId(String descId) {
		this.descId = descId;
	}
	public void setFolderName(String folderName) {
		this.folderName = folderName;
	}

 	public void doCenterShape(boolean centerShape) {
		this.centerShape = centerShape;
	}

	public void doDrawOccluder(boolean drawOccluder) {
		this.drawOccluder = drawOccluder;
	}

	public void setTexSpec(ArrayList<Coordinates2D> texSpec) {
		this.texSpec = texSpec;
	}

	public void setTexFaceSpec(ArrayList<Point3d> texFaceSpec) {
		this.texFaceSpec = texFaceSpec;
	}
	public MStickSpec getMStickSpec() {
		msSpec = new MStickSpec();
		msSpec.setMStickInfo(msShape);
        msSpec.vertex = null;

        return msSpec;
	}
	public void setMStickSpec(String s) {
		msSpec = MStickSpec.fromXml(s);
		generateStickFromSpec = true;
	}

	public static void main_db(String[] args) throws LWJGLException {
		List<BsplineObject> objs = new ArrayList<BsplineObject>();

		CreateDbDataSource dataSourceMaker = new CreateDbDataSource();
		SachDbUtil dbUtil = new SachDbUtil(dataSourceMaker.getDataSource());
		String prefix = dbUtil.readCurrentDescriptivePrefix();
		GenerationInfo info = dbUtil.readReadyGenerationInfo();
		long genNum = info.getGenId();
		int nStim = info.getStimPerLinCount();
		List<Long> ids = new ArrayList<Long>();

		prefix += "_g-" + genNum + "_l-";

		nStim = 5;
		String descId;
		for (int l=1; l<=2; l++) {
			System.out.println("Getting data for lin " + l);
			for (int ii=1; ii<=nStim; ii++) {
				descId = prefix + l + "_s-" + ii;
				long id = dbUtil.readStimObjIdFromDescriptiveId(descId);
				System.out.println("Fetching " + descId + ": " + id);

				BsplineObject bso = new BsplineObject();

				StimSpecEntry spec_general = dbUtil.readMStickSpecFromStimObjId(id);
				bso.setMStickSpec(spec_general.getSpec());

				spec_general = dbUtil.readTexSpecFromStimObjId(id);
				bso.setTexSpec(bso.convertStringToCoordinates(spec_general.getSpec()));

				spec_general = dbUtil.readTexFaceSpecFromStimObjId(id);
				bso.setTexFaceSpec(bso.convertStringToPoint3d(spec_general.getSpec()));

				spec_general = dbUtil.readStimSpecFromStimObjId(id);

				BsplineObjectSpec bsospec = BsplineObjectSpec.fromXml(spec_general.getSpec());

				bso.doCenterShape(false);
				bso.doDrawOccluder(false);
				bso.shapeParams = bsospec.getShapeParams();
				bso.shapeParams.setTagForRand(false);
				bso.shapeParams.setTagForMorph(false);
				bso.shapeParams.setTextureType(TextureType.TWOD);
				bso.shapeParams.size = 40;
				bso.shapeParams.pos = new MyPoint(0, 0);

				bso.setDescId(descId);
				ids.add(id);

				bso.createObj();

				objs.add(bso);
			}
		}

		System.out.println(objs.size() + " objects fetched. Now generating images.");

		StimTestWindow testWindow = new StimTestWindow(1000,1000,3);

		testWindow.setBackgroundColor(0,0.5f,0);
		testWindow.setSpeedInSecs(0.01);
		testWindow.setSavePNGtoDb(false);
		testWindow.setSavePNGtoFolder(true);
		testWindow.setPngMaker(new PNGmaker(dbUtil));
		testWindow.setImageFolderName(dbUtil.readCurrentDescriptivePrefix() + "_g-" + genNum + "/textureMapped");

		testWindow.setStimObjs(objs);
		testWindow.setStimObjIds(ids);

		testWindow.testDraw();				// draw object
		testWindow.close();
		System.out.println("...done saving PNGs");
	}

	public static void main(String[] args) throws LWJGLException {
		List<BsplineObject> objs = new ArrayList<BsplineObject>();
		List<Long> ids = new ArrayList<Long>();

		for (int ii=0; ii<5; ii++) {
			BsplineObject bso = new BsplineObject();
			bso.doCenterShape(false);
			bso.doDrawOccluder(false);
			bso.shapeParams.setTagForMorph(false);
			bso.shapeParams.setTagForRand(true);
			bso.shapeParams.setTextureType(TextureType.SPECULAR);
			bso.shapeParams.setColor(new RGBColor(1,1,1));
			bso.shapeParams.doClouds = true;
			bso.shapeParams.size = 12;
			bso.shapeParams.pos = new MyPoint(0, 0);

			bso.createObj();
			objs.add(bso);
			ids.add((long)ii);
		}
		StimTestWindow testWindow = new StimTestWindow(1000,1000,3);

		testWindow.setBackgroundColor(0.3f,0.3f,0.3f);
		testWindow.setSpeedInSecs(1);
		testWindow.setSavePNGtoDb(false);
		testWindow.setSavePNGtoFolder(true);
		testWindow.setPngMaker(new PNGmaker());
		testWindow.setImageFolderName("testing");

		testWindow.setStimObjs(objs);
		testWindow.setStimObjIds(ids);

		testWindow.testDraw();
		testWindow.close();

//		for (int ii=0; ii<5; ii++) {
//			objs.get(ii).shapeParams.textureType = TextureType.SHADE;
//			objs.get(ii).shapeParams.size = 12;
//			objs.get(ii).shapeParams.pos = new MyPoint(0, 0);
//			ids.set(ii, ids.get(ii) + 5);
//		}
//
//		StimTestWindow testWindow2 = new StimTestWindow(1000,1000,3);
//
//		testWindow2.setBackgroundColor(0.3f,0.3f,0.3f);
//		testWindow2.setSpeedInSecs(0.01);
//		testWindow2.setSavePNGtoDb(false);
//		testWindow2.setSavePNGtoFolder(true);
//		testWindow2.setPngMaker(new PNGmaker());
//		testWindow2.setImageFolderName("testing");
//
//		testWindow2.setStimObjs(objs);
//		testWindow2.setStimObjIds(ids);
//
//		testWindow2.setStimObjs(objs);
//		testWindow2.testDraw();
//		testWindow2.close();
	}

	private ArrayList<Coordinates2D> convertStringToCoordinates(String texSpecStr) {
		ArrayList<Coordinates2D> texSpec = new ArrayList<Coordinates2D>();
		String[] lines = texSpecStr.split("\n");
		for (String line : lines) {
			String[] coords = line.split(",");
			Coordinates2D pt = new Coordinates2D();
			pt.setX(Double.parseDouble(coords[0]));
			pt.setY(Double.parseDouble(coords[1]));
			texSpec.add(pt);
		}
		return texSpec;
	}

	private ArrayList<Point3d> convertStringToPoint3d(String texFaceSpecStr) {
		ArrayList<Point3d> texFaceSpec = new ArrayList<Point3d>();
		String[] lines = texFaceSpecStr.split("\n");
		for (String line : lines) {
			String[] coords = line.split(",");
			Point3d pt = new Point3d();
			pt.x = Double.parseDouble(coords[0]);
			pt.y = Double.parseDouble(coords[1]);
			pt.z = Double.parseDouble(coords[2]);

			texFaceSpec.add(pt);
		}
		return texFaceSpec;
	}

}
