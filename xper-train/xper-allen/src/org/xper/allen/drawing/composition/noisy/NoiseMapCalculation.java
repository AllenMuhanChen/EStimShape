package org.xper.allen.drawing.composition.noisy;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;

import javax.vecmath.Point2d;
import javax.vecmath.Point3d;

import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.drawing.Coordinates2D;

public class NoiseMapCalculation {
	private AllenMatchStick ams;


	public NoiseMapCalculation(AllenMatchStick ams) {
		this.ams = ams;
		if(ams.getnComponent()>2) {
			throw new IllegalArgumentException("This NoiseMapCalculation can"
					+ "only handle match sticks with 2 components");
		}
	}
	
	private void calculate() {
		
		List<Point2d[]> segmented2dMAxis = squash3dMAxis();
		List<Point2d[]> sortedSegmented2dMAxis = sortSegmented2dMAxis(segmented2dMAxis);
		
		
	}
	
	/**
	 * order the segments of the 2dMAxis such that the ordering
	 * can form a straight line such that the special limb is the last one.
	 * @return
	 * 
	 * CAN ONLY HANDLE AMS WITH 2 COMPONENETS!
	 */
	private List<Point2d[]> sortSegmented2dMAxis(List<Point2d[]> segmented2dMAxis){
		List<Point2d[]> sortedSegmented2dMAxis = new ArrayList<>(2);
		int firstSegment = -1;
		int lastSegment = -1;
		if(ams.getSpecialEndComp()==0) {
			firstSegment=1;
			lastSegment=0;
		} else {
			firstSegment=0;
			lastSegment=1;
		}
		sortedSegmented2dMAxis.add(0, segmented2dMAxis.get(firstSegment));
		sortedSegmented2dMAxis.add(1, segmented2dMAxis.get(lastSegment));
		return sortedSegmented2dMAxis;
	}
	
	private List<Point2d[]> squash3dMAxis() {
		List<Point2d[]>segmented2dMAxis = new LinkedList<>();
		List<Point3d[]> segmented3dMAxis = constructSegmented3dMAxis();
		for(Point3d[] axis:segmented3dMAxis) {
			Point2d axis2d[] = new Point2d[axis.length];
			for (int i=0; i<axis.length; i++) {
				axis2d[i] = new Point2d(axis[i].getX(), axis[i].getY());
			}
			segmented2dMAxis.add(axis2d);
		}
		return segmented2dMAxis;
	}
	
	private List<Point3d[]> constructSegmented3dMAxis() {
		List<Point3d[]> segmented3dMAxis = new LinkedList<>();
		for(int i=0; i<ams.getNComponent(); i++) {
			//TODO: making sure 
			segmented3dMAxis.add(ams.getTubeComp(0).getmAxisInfo().getmPts());
		}
		return segmented3dMAxis;
	}

	public AllenMatchStick getAms() {
		return ams;
	}

	public void setAms(AllenMatchStick ams) {
		this.ams = ams;
	}
}
