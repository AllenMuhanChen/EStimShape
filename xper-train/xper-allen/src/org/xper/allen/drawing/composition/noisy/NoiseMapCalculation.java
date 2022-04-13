package org.xper.allen.drawing.composition.noisy;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

import javax.vecmath.Point2d;
import javax.vecmath.Point3d;

import org.xper.allen.drawing.composition.AllenMatchStick;

public class NoiseMapCalculation {
	//INPUT FIELDS
	private AllenMatchStick ams;
	
	//CALCULATION FIELDS
	private List<Point2d> sorted2dMAxis;
	private List<Double> normalizedPositions; //between 0 and n. Should be same length as sorted2dMAxis.
	
	//MAxis Noise Maps
	private int n;
	private List<Double> noiseChanceMAxisMap;
	
	public NoiseMapCalculation(AllenMatchStick ams, double noiseOnsetPosition, double[] noiseChanceBounds) {
		this.ams = ams;
		if(ams.getnComponent()>2) {
			throw new IllegalArgumentException("This NoiseMapCalculation can"
					+ "only handle match sticks with 2 components");
		}
		this.n = ams.getnComponent();
		
		setup();
		//noiseChanceMAxisMap
		noiseChanceMAxisMap = generateLinearMAxisNoiseMap(noiseOnsetPosition, noiseChanceBounds, normalizedPositions);
	}
	
	public float calculateNoiseChanceForTriangle(Point3d[] triangleVertices) {
		double normalizedPosition = calculateNormalizedPositionofTriangle(triangleVertices);
		double noiseChance = mapNormalizedPositionToMAxisMap(normalizedPosition, noiseChanceMAxisMap, normalizedPositions);
		return (float) noiseChance;
	}
	
	
	private void setup() {
		List<Point2d[]> segmented2dMAxis = squash3dMAxis();
		List<Point2d[]> sortedSegmented2dMAxis = sortSegmented2dMAxis(segmented2dMAxis);
		this.sorted2dMAxis = stitchSegmented2dMAxis(sortedSegmented2dMAxis);
		
		//TODO: INCLUDE IN SETUP AN ARRAY OF NORMALIZED POSITIONS. 
		this.normalizedPositions = normalizePositionsAlongMAxis(sortedSegmented2dMAxis);
	}
	
	private double mapNormalizedPositionToMAxisMap(Double normalizedPosition, List<Double> noiseChanceMAxisMap, List<Double> normalizedPositions) {
		return noiseChanceMAxisMap.get(normalizedPositions.indexOf(normalizedPosition));
	}
	
	/**Generates noise map to map positions along MAXis to percentage change of noising. 
	 * Linear: From onset position to end of limb, probability decreases linearally from starting point to zero. 
	 * 
	 * @param noiseOnsetPosition: normalized between 0-n, with each integer value 
	 * referring to the start of limb n.
	 * @param noiseBounds: from 0 to 1, indx 0: lowest percentage chance, indx 1: highest perc chc 
	 */
	private List<Double> generateLinearMAxisNoiseMap(double noiseOnsetPosition, double[] noiseChanceBounds, List<Double> normalizedPositions) {
		List<Double> noiseChanceMAxisMap = new LinkedList<>();
		double linearRampLength = n-noiseOnsetPosition;
		for(double normPos:normalizedPositions) {
			//Not yet in noised zone
			if(normPos < noiseOnsetPosition) {
				noiseChanceMAxisMap.add(noiseChanceBounds[0]);
			}
			//Enter noise zone
			else {
				double lengthRemaining = n - normPos;
				double noiseChance = (lengthRemaining/linearRampLength)*noiseChanceBounds[0] + noiseChanceBounds[1];
				noiseChanceMAxisMap.add(noiseChance);
			}
		}
		
		return noiseChanceMAxisMap;
	}
	/**
	 * Between 0 and n, with n being the number of limbs. (In this case, 2)
	 * Finds closest medial axis location to the center of the triangle. 
	 * @param triangleVertices
	 * @return
	 */
	private double calculateNormalizedPositionofTriangle(Point3d[] triangleVertices) {
		Point2d triangleCenter = new Point2d();
		double xSum = triangleVertices[0].getX()+triangleVertices[1].getX()+triangleVertices[2].getX();
		double ySum = triangleVertices[0].getY()+triangleVertices[1].getY()+triangleVertices[2].getZ();
		
		triangleCenter.setX(xSum/3);
		triangleCenter.setY(ySum/3);
		
		List<Double> distances = new LinkedList<>();
		for(int i=0; i<sorted2dMAxis.size();i++) {
			distances.add(triangleCenter.distance(sorted2dMAxis.get(i)));
		}
		int minDistanceIndx = distances.indexOf(Collections.min(distances));
		
		//TODO: proper normalized position here. with n=1, being the junction, n=2 being end of special Comp. 
		double normalizedPosition = normalizedPositions.get(minDistanceIndx); 
		
		return normalizedPosition;
		
	}
	
	private List<Double> normalizePositionsAlongMAxis(List<Point2d[]> sortedSegmented2dMAxis){
		List<Double> normalizedPosition = new LinkedList<>();
		for(Point2d[] axis: sortedSegmented2dMAxis) {
			double axisNum = sortedSegmented2dMAxis.indexOf(axis);
			for(int i=0; i<axis.length; i++){
				double withinAxisPos = (double) i / (double) (axis.length-1);
				normalizedPosition.add(axisNum+withinAxisPos);
			}
		}
		
		return normalizedPosition;
	}
	
	
	private List<Point2d> stitchSegmented2dMAxis(List<Point2d[]> segmented2dMAxis){
		List<Point2d> continuous2dMAxis = new LinkedList<Point2d>();
		for(Point2d[] axis:segmented2dMAxis) {
			continuous2dMAxis.addAll(Arrays.asList(axis));
		}
		return continuous2dMAxis;
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
		for(int i=1; i<=ams.getNComponent(); i++) {
			//TODO: making sure 
			segmented3dMAxis.add(ams.getTubeComp(i).getmAxisInfo().getmPts());
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
