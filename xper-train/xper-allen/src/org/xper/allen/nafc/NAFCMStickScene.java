package org.xper.allen.nafc;

import java.util.LinkedList;
import java.util.List;

import javax.vecmath.Point3d;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.png.ImageDimensions;
import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.allen.specs.AllenMStickSpec;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.experiment.ExperimentTask;

public class NAFCMStickScene extends AbstractTaskScene implements NAFCTaskScene{
	int numChoices;
	@Dependency
	double distance;
	@Dependency
	double screenWidth;
	@Dependency
	double screenHeight;
	@Dependency
	double[] backgroundColor;
	
	Coordinates2D[] choiceLocations;
	Coordinates2D sampleLocation;
	ImageDimensions sampleDimensions;
	ImageDimensions[] choiceDimensions;
	
	AllenMStickSpec sampleSpec;
	AllenMStickSpec[] choiceSpec;
	
	AllenMatchStick sampleMStick ;
	List<AllenMatchStick> choiceMStick = new LinkedList<AllenMatchStick>();
	
	public void initGL(int w, int h) {

		super.setUseStencil(true);
		super.initGL(w, h);
		//System.out.println("JK 32838 w = " + screenWidth + ", h = " + screenHeight);
		
		GL11.glClearColor((float)backgroundColor[0], (float)backgroundColor[1], (float)backgroundColor[2], 0.0f);          
		GL11.glViewport(0,0,w,h);
        GL11.glMatrixMode(GL11.GL_MODELVIEW); 
        GL11.glMatrixMode(GL11.GL_PROJECTION);
        GL11.glLoadIdentity();
		
        GL11.glOrtho(0, w, h, 0, 1, -1);
        GL11.glMatrixMode(GL11.GL_MODELVIEW);
	}
	
	@Override
	public void trialStart(TrialContext context) {
		NAFCExperimentTask task = (NAFCExperimentTask) context.getCurrentTask();
		numChoices = task.getChoiceSpec().length;
		sampleMStick = new AllenMatchStick();
		for (int i=0; i<numChoices; i++){
			choiceMStick.add(new AllenMatchStick());
		}
	}
	
	@Override
	public void setSample(NAFCExperimentTask task) {
		sampleSpec = AllenMStickSpec.fromXml(task.getSampleSpec());	
		sampleSpec.setMStickInfo(sampleMStick);
		
	}

	@Override
	public void setChoice(NAFCExperimentTask task) {	
		for (int i=0; i< numChoices; i++){
		choiceSpec[i] = AllenMStickSpec.fromXml(task.getChoiceSpec()[i]);
		choiceSpec[i].setMStickInfo(choiceMStick.get(i));
		}
		
	}

	@Override
	public void drawSample(Context context, boolean fixationOn) {
		//Convert Sample Location to mm and center shape to this location
		Point3d newLocation = new Point3d();
		newLocation.x = context.getRenderer().deg2mm(sampleLocation.getX());
		newLocation.y = context.getRenderer().deg2mm(sampleLocation.getY());
		newLocation.z = 0;
		sampleMStick.centerShapeAtPoint(-1, newLocation);
		
		sampleMStick.draw();

	}

	@Override
	public void drawChoice(Context context, boolean fixationOn) {
		for(int i=0; i<numChoices; i++){
			//Convert Sample Location to mm and center shape to this location
			Point3d newLocation = new Point3d();
			newLocation.x = context.getRenderer().deg2mm(choiceLocations[i].getX());
			newLocation.y = context.getRenderer().deg2mm(choiceLocations[i].getY());
			newLocation.z = 0;
			choiceMStick.get(i).centerShapeAtPoint(-1, newLocation);
			
			choiceMStick.get(i).draw();
		}
		
	}
	

	@Override
	public void setTask(ExperimentTask task) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void nextMarker() {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void drawTask(Context context, boolean fixationOn) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void drawStimulus(Context context) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void drawBlank(Context context, boolean fixationOn, boolean markerOn) {
		// TODO Auto-generated method stub
		
	}



	@Override
	public void trialStop(TrialContext context) {
		// TODO Auto-generated method stub
		
	}

	public double getDistance() {
		return distance;
	}

	public void setDistance(double distance) {
		this.distance = distance;
	}

	public double getScreenWidth() {
		return screenWidth;
	}

	public void setScreenWidth(double screenWidth) {
		this.screenWidth = screenWidth;
	}

	public double getScreenHeight() {
		return screenHeight;
	}

	public void setScreenHeight(double screenHeight) {
		this.screenHeight = screenHeight;
	}

	public double[] getBackgroundColor() {
		return backgroundColor;
	}

	public void setBackgroundColor(double[] backgroundColor) {
		this.backgroundColor = backgroundColor;
	}


}


