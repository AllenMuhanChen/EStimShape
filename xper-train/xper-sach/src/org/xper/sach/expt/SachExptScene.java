package org.xper.sach.expt;

import java.util.ArrayList;
import java.util.List;

import javax.vecmath.Point3d;

import org.xper.Dependency;
import org.xper.classic.vo.TrialContext;
import org.xper.db.vo.StimSpecEntry;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.experiment.ExperimentTask;
import org.xper.sach.AbstractSachTaskScene;
import org.xper.sach.drawing.screenobj.DiskObject;
import org.xper.sach.drawing.screenobj.RectangleObject;
import org.xper.sach.drawing.stick.MStickSpec;
import org.xper.sach.drawing.stimuli.BsplineObject;
import org.xper.sach.drawing.stimuli.BsplineObjectSpec;
//import org.xper.sach.renderer.SachPerspectiveStereoRenderer;
import org.xper.sach.util.SachDbUtil;
import org.xper.sach.vo.SachTrialContext;

public class SachExptScene extends AbstractSachTaskScene {
	
	@Dependency
	SachDbUtil dbUtil;
	
	// --- initialize response target
	DiskObject responseSpot = new DiskObject();		// to change specs, change in DiskObject
	boolean drawResponseSpot;						// this is the target position marker (for behavioral trials)
	RectangleObject extraFixationSpot = new RectangleObject(1.0f,1.0f,0.0f,5,5);
	//BsplineObject spline = new BsplineObject();
	
	RGBColor stimForegroundColor;
	
	List<BsplineObject> objects = new ArrayList<BsplineObject>();
	SachExptSpec spec = new SachExptSpec();
	
	public void initGL(int w, int h) {
		super.initGL(w, h);
		
//		// set response spot size and location:
//		SachPerspectiveStereoRenderer rend = (SachPerspectiveStereoRenderer)this.renderer;
//		double d = rend.getDistance();
		
	}

	public void setTask(ExperimentTask task) {
		objects.clear();
		spec = SachExptSpec.fromXml(task.getStimSpec());
		
		for (int i = 0; i < spec.getStimObjIdCount(); i ++) {
			long id = spec.getStimObjId(i);
			StimSpecEntry bsoSpec_general = dbUtil.readStimSpecFromStimObjId(id);
			BsplineObjectSpec bsoSpec = BsplineObjectSpec.fromXml(bsoSpec_general.getSpec()); 
			
			StimSpecEntry msSpec_general = dbUtil.readMStickSpecFromStimObjId(id);
			
			BsplineObject obj = new BsplineObject();
			
			if (!msSpec_general.getSpec().isEmpty()) {
				MStickSpec msSpec = MStickSpec.fromXml(msSpec_general.getSpec());
				obj.setMStickSpec(msSpec.toXml());
				
				bsoSpec.getShapeParams().setTagForMorph(false);
				bsoSpec.getShapeParams().setTagForRand(false);
			}
			
//			try {
//				if (bsoSpec.getStimType() != "BLANK") {
//					StimSpecEntry texSpec_general = dbUtil.readTexSpecFromStimObjId(id);
//					if (!texSpec_general.getSpec().isEmpty()) {
//						String texSpecStr = texSpec_general.getSpec();
//						obj.setTexSpec(convertStringToCoordinates(texSpecStr));
//					}
//					StimSpecEntry texFaceSpec_general = dbUtil.readTexFaceSpecFromStimObjId(id);
//					if (!texFaceSpec_general.getSpec().isEmpty()) {
//						String texFaceSpecStr = texFaceSpec_general.getSpec();
//						obj.setTexFaceSpec(convertStringToPoint3d(texFaceSpecStr));
//					}
//				}
//			} catch (NullPointerException ex) {
//				
//			}
			
			obj.setDescId(dbUtil.readDescriptiveIdFromStimObjId(id));
			obj.setFolderName(dbUtil.readCurrentDescriptivePrefixAndGen());
			obj.setSpec(bsoSpec.toXml());
			objects.add(obj);
		}
	}

	public void drawStimulus(Context context) {
		TrialContext c = (TrialContext)context;
		if (drawResponseSpot) responseSpot.draw(c); 
		
		int index = c.getSlideIndex();
		int numObjs = objects.size();
		
//		System.out.println("drawStim slide=" + index);
		if ((index >= 0) && (index < numObjs)) {
			BsplineObject obj = objects.get(index);
			obj.draw(c);
		}
	}

	protected void drawTargetObjects(Context context) {
		SachTrialContext c = (SachTrialContext)context;
		if (drawResponseSpot) responseSpot.draw(c);		
		
		// --- redraw the target, to show the object at the target position (for training):
		int index = c.getSlideIndex();
		long targetIndex = c.getTargetIndex();
		
		//System.out.println("drawTargetObjs slide=" + index);

		if (index >= 0 && index < objects.size()) {
			if (targetIndex >= 0) {
//				BsplineObject obj = objects.get(index);
//				
//				double xPos = c.getTargetPos().getX();	// get the target positions from the trial context
//				double yPos = c.getTargetPos().getY();
//				xPos = c.getRenderer().deg2mm(xPos);	// convert units
//				yPos = c.getRenderer().deg2mm(yPos);
//
//				obj.setxPos(xPos);		// shift the obj position to that of the target position
//				obj.setyPos(yPos);
//				obj.draw(c);			// show obj at target position
				
				extraFixationSpot.drawRectangle(c);
			}
			
		}

				// --- for showing a simple circle around target position:
		//SachExperimentUtil.drawTargetEyeWindow(c.getRenderer(), c.getTargetPos(), c.getTargetEyeWindowSize(), new RGBColor(1f, 1f, 0f)); 

	}
	
	protected void drawCustomBlank(Context context) {
		// draw your customized blank screen
		if (drawResponseSpot) responseSpot.draw(context); 

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
	
	
	public boolean isDrawResponseSpot() {
		return drawResponseSpot;
	}
	public void setDrawResponseSpot(boolean drawResponseSpot) {
		this.drawResponseSpot = drawResponseSpot;
	}
	
	public RGBColor getStimForegroundColor() {
		return stimForegroundColor;
	}
	public void setStimForegroundColor(RGBColor fColor) {
		this.stimForegroundColor = fColor;
	}
	
	

	/**
	 * @return the dbUtil
	 */
	public SachDbUtil getDbUtil() {
		return dbUtil;
	}

	/**
	 * @param dbUtil the dbUtil to set
	 */
	public void setDbUtil(SachDbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}

//	public void releaseStimulus(TrialContext context) {
//		// TODO Auto-generated method stub
//		TrialContext c = (TrialContext)context;
//		
//		int index = c.getSlideIndex();
//		int numObjs = objects.size();
//		
////		System.out.println("drawStim slide=" + index);
//		if ((index >= 0) && (index < numObjs)) {
//			BsplineObject obj = objects.get(index);
//			obj.releaseAllTextures();
//		}
//	}
	
	public void releaseAllStimuli(TrialContext context) {
		
		int numObjs = objects.size();
		
		for (int index=0; index < numObjs; index++) {
			BsplineObject obj = objects.get(index);
			obj.releaseAllTextures();
		}
	}
	
	
}
