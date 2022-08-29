package org.xper.sach.analysis;

import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.ArrayList;
import java.util.List;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

import org.jzy3d.plot3d.rendering.image.GLImage;
import org.lwjgl.opengl.GL11;
import org.xper.drawing.RGBColor;
import org.xper.sach.drawing.StimTestWindow;
import org.xper.sach.drawing.stick.MStickSpec;
import org.xper.sach.drawing.stimuli.BsplineObject;
import org.xper.sach.drawing.stimuli.BsplineObjectSpec;
import org.xper.sach.util.BlenderRunnable;
import org.xper.sach.util.CreateDbDataSource;
import org.xper.sach.util.SachDbUtil;

public class PNGmaker {

	SachDbUtil dbUtil;	
	List<BsplineObjectSpec> specs = new ArrayList<BsplineObjectSpec>();
//	List<BsplineObject> objs = new ArrayList<BsplineObject>();
//	List<Drawable> objs = new ArrayList<Drawable>();
	
	int height = 600;	// height & width of stim window	
	int width = 600;

	RGBColor stimForegroundColor_shape1;
	RGBColor stimForegroundColor_shape2;
	RGBColor stimBackgroundColor;
	
	StimTestWindow testWindow;
	
	public PNGmaker(BsplineObjectSpec spec) {
		specs.add(spec);
		createAndSavePNGs();
	}

	public PNGmaker() {}
	
	public PNGmaker(SachDbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}
	
//	public PNGmaker(List<BsplineObjectSpec> specs) {
//		this.specs = specs;
//		createAndSavePNGs();
//	}

//	public PNGmaker(List<Long> stimObjIds) {
//		// use stimObjId to get spec from db, then create objs
//		List<Drawable> objs = spec2obj(id2spec(stimObjIds));
//		createAndSavePNGsfromObjs(objs,stimObjIds);
//	}
	
	public void MakeFromIds(List<Long> stimObjIds, String imageFolderName) {
		// use stimObjId to get spec from db, then create objs
		List<BsplineObject> objs = spec2obj(id2spec(stimObjIds),stimObjIds);
		
		System.out.println("Done creating stimuli. Now writing specs to database.");
		// update the javaspec and the mstickspec in the database
		
		for (int i=0; i<objs.size(); i++) {
			BsplineObject obj = objs.get(i);
			MStickSpec msSpec = obj.getMStickSpec();
			
			System.out.println("Saving stick spec for stimulus " + (i+1) + " to database.");
			
			// write mstickspec
			dbUtil.writeMStickSpec(stimObjIds.get(i), msSpec.toXml());
			
			// get and write actual face spec
			String descId = dbUtil.readDescriptiveIdFromStimObjId(stimObjIds.get(i));
//			if (obj.getSpec().getShapeParams().getSaveVertSpec()) {
//				String vertSpec = vectToStr(obj.getMsShape().obj1.vect_info, obj.getMsShape().obj1.nVect);
//				String faceSpec = facToStr(obj.getMsShape().obj1.facInfo, obj.getMsShape().obj1.nFac);
//				String normSpec = normToStr(obj.getMsShape().obj1.normMat_info, obj.getMsShape().obj1.nVect); // new String(); //
//				dbUtil.writeVertSpec(stimObjIds.get(i),descId, vertSpec,faceSpec,normSpec);
//			} else
			try {
				dbUtil.writeVertSpec(stimObjIds.get(i), descId, "", "", "");
			} catch (Exception e) {
				System.out.println("Vert Spec already exists in DB");
			}
			
			//BsplineObjectSpec bsoSpec = obj.getSpec();
			// dbUtil.updateJavaSpec(stimObjIds.get(i), bsoSpec.toXml());
		}

		 try {
			 createAndSavePNGsfromObjs(stimObjIds, objs, imageFolderName);
		 }
		 catch (Exception e){
			 System.out.println("Couldn't create thumbnails");
		 }
	}
	
	private List<BsplineObjectSpec> id2spec(List<Long> stimObjIds) {
		List<BsplineObjectSpec> specs = new ArrayList<BsplineObjectSpec>();
		for (Long id : stimObjIds) {
			String s = dbUtil.readStimSpecFromStimObjId(id).getSpec();
			BsplineObjectSpec spec = BsplineObjectSpec.fromXml(s);
			specs.add(spec);
		}
		return specs;
	}
	
	private List<BsplineObject> spec2obj(List<BsplineObjectSpec> specs,List<Long> stimObjIds) {
		List<BsplineObject> objs = new ArrayList<BsplineObject>();
		
		System.out.println("Retrieved shape specs. Now generating stick specs.");
		for (int i=0; i<specs.size(); i++) {
			System.out.println("Generating stick spec for stimulus " + (i+1) + ": id = " + stimObjIds.get(i) + ". Generating = " + specs.get(i).getShapeParams().getTagForRand() + "; morphing = " + specs.get(i).getShapeParams().getTagForMorph() + ".");
			
			BsplineObject obj = new BsplineObject();
			
			if (specs.get(i).getShapeParams().getTagForMorph()) {
				String mstickspec = dbUtil.readMStickSpecFromStimObjId(stimObjIds.get(i)).getSpec();
				obj.setMStickSpec(mstickspec);
			} else if (!specs.get(i).getShapeParams().getTagForRand()) {
				String mstickspec = dbUtil.readMStickSpecFromStimObjId(stimObjIds.get(i)).getSpec();
				obj.setMStickSpec(mstickspec);
			}
			
			obj.doCenterShape(true);
			obj.doDrawOccluder(false);
			
			obj.setSpec(specs.get(i).toXml());
			
			objs.add(obj);
		}
		// specs -> objs, then pass to createAndSavePNGs
		return objs;
	}

	public void createAndSavePNGsfromObjs(List<Long> stimObjIds,List<BsplineObject> objs, String imageFolderName) {

		testWindow = new StimTestWindow(height,width);
//		testWindow.setDoPause(true);
		testWindow.setBackgroundColor(stimBackgroundColor.getRed(), stimBackgroundColor.getGreen(), stimBackgroundColor.getBlue());
		testWindow.setSpeedInSecs(1);
		testWindow.setSavePNGtoDb(true);
		testWindow.setPngMaker(this);
		testWindow.setImageFolderName(imageFolderName);

		testWindow.setStimObjs(objs);
		testWindow.setStimObjIds(stimObjIds);
		
		testWindow.testDraw();				// draw object
		testWindow.close();
		System.out.println("...done saving PNGs");
	}
	
	public void lateSave(List<Long> stimObjIds, String imageFolderName) {
		List<BsplineObjectSpec> specs = new ArrayList<BsplineObjectSpec>();
		for (Long id : stimObjIds) {
			String s = dbUtil.readStimSpecFromStimObjId(id).getSpec();
			BsplineObjectSpec spec = BsplineObjectSpec.fromXml(s);
			spec.getShapeParams().setTagForMorph(false);
			spec.getShapeParams().setTagForRand(false);
			specs.add(spec);
		}
		
		List<BsplineObject> objs = spec2obj(specs,stimObjIds);
		
		for (int i=0; i<objs.size(); i++) {
			BsplineObject obj = objs.get(i);
			
			// get and write actual face spec
			if (obj.getSpec().getShapeParams().getSaveVertSpec()) {
				System.out.println("Saving vert spec for stimulus " + (i+1) + " to database.");
				
				String vertSpec = vectToStr(obj.getMsShape().obj1.vect_info, obj.getMsShape().obj1.nVect);
				String faceSpec = facToStr(obj.getMsShape().obj1.facInfo, obj.getMsShape().obj1.nFac);
				String normSpec = new String(); // normToStr(obj.getMsShape().obj1.normMat_info, obj.getMsShape().obj1.nVect); // new String(); //
				dbUtil.writeVertSpec_update(stimObjIds.get(i),vertSpec,faceSpec,normSpec);
				
				
				String appPath = "/Applications/Blender.app/Contents/MacOS/blender";
				String descId = dbUtil.readDescriptiveIdFromStimObjId(stimObjIds.get(i)); 
				
				List<String> args = new ArrayList<String>();
				args.add(appPath);
				args.add("--background");
				args.add("--python");
				args.add("");
				args.add("--");
				args.add(descId);
				
				BlenderRunnable visibleRunner = new BlenderRunnable();
				String scriptPath = "/Users/ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectGetVisible/dbExchange.py";
				args.set(3, scriptPath);
				visibleRunner.setArgs(args);
				visibleRunner.run();
				 
//				BlenderRunnable photoRunner = new BlenderRunnable();
//				scriptPath = "/Users/ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectMakePhoto/dbExchange.py";
//				args.set(3, scriptPath);
//				photoRunner.setArgs(args);
//				photoRunner.run();
				
				BlenderRunnable drapeRunner = new BlenderRunnable();
				scriptPath = "/Users/ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectDrape/dbExchange.py";
				args.set(3, scriptPath);
				drapeRunner.setArgs(args);
				drapeRunner.run();
			}
		}
		//createAndSavePNGsfromObjs(stimObjIds,objs,imageFolderName);
		
//		BlenderRunnable photoRunner = new BlenderRunnable();
//		List<String> args = new ArrayList<String>();
//		args.add("ssh");
//		args.add("ram@172.30.9.11");
//		args.add("\"/home/ram/projectMakePhoto/masterSubmitScript.sh " + imageFolderName + "\"");
//		photoRunner.setArgs(args);
//		photoRunner.setDoWaitFor(false);
//		photoRunner.run();
	}
	
	
	public void createAndSavePNGs() {

		StimTestWindow testWindow = new StimTestWindow(height,width);
//		testWindow.setDoPause(true);
		testWindow.setBackgroundColor(stimBackgroundColor.getRed(), stimBackgroundColor.getGreen(), stimBackgroundColor.getBlue());
		testWindow.setSpeedInSecs(1.0);
		testWindow.setSavePNGtoDb(true);
		testWindow.setPngMaker(this);

		System.out.println("creating PNGs from specs...");

		for (BsplineObjectSpec spec : specs) {
			BsplineObject obj = new BsplineObject();
//			obj.setCantFail(true);
			obj.setSpec(spec.toXml());
			testWindow.setStimObjs(obj);			// add object to be drawn
		}

		testWindow.testDraw();				// draw object
//		testWindow.close();
		System.out.println("...done saving PNGs");
	}

	public void run() { // NOT USING NOW
		// this only works for one obj and it became to complicated to fix, so instead we will call 
		// PNG maker from StimTestWindow -shs
		//		int height = 200;	// height & width of stim window	
		//		int width = 200;
		//		double mag = 2;		// magnification of stimulus

		// -- for testing:
		CreateDbDataSource dataSourceMaker = new CreateDbDataSource();
		setDbUtil(new SachDbUtil(dataSourceMaker.getDataSource()));
		// --

		StimTestWindow testWindow = new StimTestWindow(height,width);
		testWindow.setDoPause(true);
		testWindow.setSpeedInSecs(1.0);

		System.out.println("creating PNG from spec");

		for (BsplineObjectSpec spec : specs) {

			BsplineObject obj = new BsplineObject();
//			obj.setCantFail(true);
			obj.setSpec(spec.toXml());
			testWindow.setStimObjs(obj);			// add object to be drawn
			//			System.out.println();

			//testWindow.experimentResume();

			testWindow.testDraw();				// draw object

			// capture image here:
			//		ImgBinData img = new ImgBinData();
			int h = testWindow.getHeight();
			int w = testWindow.getWidth();
			byte[] data = screenShotBinary(w,h);  

			System.out.println("the img data length is " + data.length);

			// save image:
//			long id = spec.getStimObjId();

//			dbUtil.writeThumbnail(id,data);
//			System.out.println("saved stimSpecId: " + id);
//
//			// test read:
//			byte[] dataOut = dbUtil.readThumbnail(id);
//			boolean b = SachMathUtil.isArrEqual(data,dataOut);
//			System.out.println("dataIn = dataOut is " + b);

			//testWindow.experimentResume();

		}

		//testWindow.close();
	}
	
	public void makePNGfromScreenShot(long stimObjId, int height, int width,String imageFolderName) {
		// when this runs, it takes a screenshot and saves it with the stimObjId label
		// capture image here:
		//		ImgBinData img = new ImgBinData();
		byte[] data = screenShotBinary(width,height);  

		// System.out.println("the img data length is " + data.length);

		// save image:
		dbUtil.writeThumbnail(stimObjId,data);
		try {
			File dir = new File("images/" + imageFolderName);
			dir.mkdirs();
			
			FileOutputStream fos = new FileOutputStream("images/" + imageFolderName + "/" + stimObjId + ".png");
		    fos.write(data);
		    fos.close();
		} 
		catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
		
//		System.out.println("saved stimSpecId: " + stimObjId);

		//		// test read:
		//		byte[] dataOut = dbUtil.readThumbnail(stimObjId);
		//		boolean b = SachMathUtil.isArrEqual(data,dataOut);
		//		System.out.println("dataIn = dataOut is " + b);
	}
	
	public void makePNGfromScreenShot_folderSaveOnly(long stimObjId, int height, int width,String imageFolderName) {
		// when this runs, it takes a screenshot and saves it with the stimObjId label
		// capture image here:
		//		ImgBinData img = new ImgBinData();
		byte[] data = screenShotBinary(width,height);  

		// System.out.println("the img data length is " + data.length);

		// save image:
		try {
			File dir = new File("images/" + imageFolderName);
			dir.mkdirs();
			
			FileOutputStream fos = new FileOutputStream("images/" + imageFolderName + "/" + stimObjId + ".png");
		    fos.write(data);
		    fos.close();
		} 
		catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
		
//		System.out.println("saved stimSpecId: " + stimObjId);

		//		// test read:
		//		byte[] dataOut = dbUtil.readThumbnail(stimObjId);
		//		boolean b = SachMathUtil.isArrEqual(data,dataOut);
		//		System.out.println("dataIn = dataOut is " + b);
	}

	private byte[] screenShotBinary(int width, int height) 
	{
		return screenShotBinary(width,height,"");
	}

	private byte[] screenShotBinary(int width, int height, String filename) 
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
			// Create a BufferedImage with the RGB pixels then save as PNG
			BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
			image.setRGB(0, 0, width, height, pixels, 0, width);

			//javax.imageio.ImageIO.write(image, "png", new File(saveFilename));

			javax.imageio.ImageIO.write(image, "png", out);
			byte[] data = out.toByteArray();

			//System.out.println("the img data length is " + data.length);

			// I decide to also save the file to harddisk this moment since it will be easier to read from Matlab
			if (filename.length() > 0) {
				//				String dir = "./matlabSimpleAnalysis/matlabPng/";
				//				String saveFilename = dir + filename + ".png";
				//				javax.imageio.ImageIO.write(image, "png", new File(saveFilename));
			}

			return data;
		}
		catch (Exception e) {
			System.out.println("screenShot(): exception " + e);
			return null;
		}
	}

	/**
	locate memory, subFunction of screenShot
	 */
	public static ByteBuffer allocBytes(int howmany) {
		final int SIZE_BYTE = 4;
		return ByteBuffer.allocateDirect(howmany * SIZE_BYTE).order(ByteOrder.nativeOrder());
	}

	private String vectToStr(Point3d[] vect, int nVect) {
		String str = new String();
		
		for(int i=1; i<=nVect; i++) {
			str = str + vect[i].x + "," + vect[i].y + "," + vect[i].z + "\n";
		}
		return str;
	}
	
	private String facToStr(int[][] fac, int nFace) {
		String str = new String();
		for(int i=0; i<nFace; i++) {
			str = str + fac[i][0] + "," + fac[i][1] + "," + fac[i][2] + "\n";
		}
		return str;
	}
	
	private String normToStr(Vector3d[] norm, int nVect) {
		String str = new String();
		for(int i=1; i<=nVect; i++) {
			str = str + norm[i].x + "," + norm[i].y + "," + norm[i].z + "\n";
		}
		return str;
	}
	
	
	private void createDbUtil() {
		// -- for testing only
		CreateDbDataSource dataSourceMaker = new CreateDbDataSource();
		setDbUtil(new SachDbUtil(dataSourceMaker.getDataSource()));
	}

	public void setDbUtil(SachDbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}

	public List<BsplineObjectSpec> getSpecs() {
		return specs;
	}

	public void setSpecs(List<BsplineObjectSpec> specs) {
		this.specs = specs;
	}
	
	public RGBColor getStimForegroundColor(int shapeNum) {
		if (shapeNum == 1)
			return stimForegroundColor_shape1;
		else
			return stimForegroundColor_shape1;
	}
	public void setStimForegroundColor(RGBColor fColor,int shapeNum) {
		if (shapeNum == 1)
			this.stimForegroundColor_shape1 = fColor;
		else
			this.stimForegroundColor_shape2 = fColor;
	}
	
	public RGBColor getStimBackgroundColor() {
		return stimBackgroundColor;
	}
	public void setStimBackgroundColor(RGBColor bColor) {
		this.stimBackgroundColor = bColor;
	}


}
