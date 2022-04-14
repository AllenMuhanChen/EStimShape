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
	private List<Point2d[]> sortedSegmented2dMAxis;
	private List<Integer> sortedSegmentIds; //IDs associated with the sorted segments. 
	private List<Double> normalizedPositions; //between 0 and n. Should be same length as sorted2dMAxis.


	//MAxis Noise Maps
	private int n;
	private List<Double> noiseChanceMAxisMap;

	public NoiseMapCalculation(AllenMatchStick ams, double[] noiseChanceBounds, double[] noiseChanceBoundPositions) {
		this.ams = ams;
		if(ams.getnComponent()>2) {
			throw new IllegalArgumentException("This NoiseMapCalculation can"
					+ "only handle match sticks with 2 components");
		}
		this.n = ams.getnComponent();

		setup();
		//noiseChanceMAxisMap
		noiseChanceMAxisMap = generateLinearMAxisNoiseMap(noiseChanceBounds, noiseChanceBoundPositions, normalizedPositions);
	}

	public float calculateNoiseChanceForTriangle(Point3d[] triangleVertices, int tubeId, double scale) {
		double normalizedPosition = calculateNormalizedPositionofTriangle_targetLimbOnly(triangleVertices, tubeId, scale);
		double noiseChance = mapNormalizedPositionToMAxisMap(normalizedPosition, noiseChanceMAxisMap, normalizedPositions);
		return (float) noiseChance;
	}


	private void setup() {
		List<Point2d[]> segmented2dMAxis = squash3dMAxis();
		sortSegmented2dMAxis(segmented2dMAxis);
		stitchSegmented2dMAxis(sortedSegmented2dMAxis);

		//TODO: INCLUDE IN SETUP AN ARRAY OF NORMALIZED POSITIONS. 
		normalizePositionsAlongMAxis(sortedSegmented2dMAxis);
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
	private List<Double> generateLinearMAxisNoiseMap(double[] noiseChanceBounds, double[] noiseChanceBoundPositions, List<Double> normalizedPositions) {
		List<Double> noiseChanceMAxisMap = new LinkedList<>();
		double linearRampLength = (double) noiseChanceBoundPositions[1]- (double) noiseChanceBoundPositions[0];
		for(double normPos:normalizedPositions) {
			//Not yet in noised zone
			if(normPos < noiseChanceBoundPositions[0]) {
				noiseChanceMAxisMap.add(noiseChanceBounds[0]);
			}
			//Enter noise ramp zone
			else if (normPos >= noiseChanceBoundPositions[0] && normPos<=noiseChanceBoundPositions[1]){
				double length = (double) normPos - noiseChanceBoundPositions[0];
				double noiseChance = (length/linearRampLength)*(noiseChanceBounds[1] - noiseChanceBounds[0]) + noiseChanceBounds[0];
//				System.out.println("AC938455943: NOISE CHANCE" + noiseChance);
//				System.out.println("AC938455943: NORM POS" + normPos);
				noiseChanceMAxisMap.add(noiseChance);
			}
			//Leave noise ramp zone.
			else {
//				System.out.println("AC: WE'VE ADDED HIGHEST");
				noiseChanceMAxisMap.add(noiseChanceBounds[1]);
			}
		}

		return noiseChanceMAxisMap;
	}
	
	
	/**
	 * Uses target MAxis (MAxis of the limb that the vertex is part of)
	 * EXCEPT for in the junctions, where it can use information from both.  
	 * 
	 * Between 0 and n, with n being the number of limbs. (In this case, 2)
	 * Finds closest medial axis location to the center of the triangle. 
	 * @param triangleVertices
	 * @return
	 */
	private double calculateNormalizedPositionofTriangle(Point3d[] triangleVertices, int id, double scale) {
		Point2d triangleCenter = new Point2d();
		double xSum = triangleVertices[0].getX()+triangleVertices[1].getX()+triangleVertices[2].getX();
		double ySum = triangleVertices[0].getY()+triangleVertices[1].getY()+triangleVertices[2].getY();
		
		triangleCenter.setX(xSum/3/scale);
		triangleCenter.setY(ySum/3/scale);

		List<Double> distances = new LinkedList<>();
	

		for(Point2d point: sorted2dMAxis) {

			distances.add(triangleCenter.distance(point));

		}


		int minDistanceIndx = distances.indexOf(Collections.min(distances));


		//TODO: proper normalized position here. with n=1, being the junction, n=2 being end of special Comp.
		double normalizedPosition = normalizedPositions.get(minDistanceIndx); 
//		System.out.println("ACNORM: " + normalizedPosition);
		return normalizedPosition;

	}

	private void normalizePositionsAlongMAxis(List<Point2d[]> sortedSegmented2dMAxis){
		List<Double> normalizedPosition = new LinkedList<>();
		for(Point2d[] axis: sortedSegmented2dMAxis) {
			double axisNum = sortedSegmented2dMAxis.indexOf(axis);
			for(int i=0; i<axis.length; i++){
				double withinAxisPos = (double) i / (double) (axis.length-1);
				normalizedPosition.add(axisNum+withinAxisPos);
			}
		}

		this.normalizedPositions = normalizedPosition;
	}


	private void stitchSegmented2dMAxis(List<Point2d[]> segmented2dMAxis){
		List<Point2d> continuous2dMAxis = new LinkedList<Point2d>();
		for(Point2d[] axis:segmented2dMAxis) {
			continuous2dMAxis.addAll(Arrays.asList(axis));
		}
		this.sorted2dMAxis = continuous2dMAxis;
	}

	/**
	 * order the segments of the 2dMAxis such that the ordering
	 * can form a straight line such that the special limb is the last one.
	 * 
	 * Then sorts the MAxis mpts within each segment as well such that they line up
	 * @return
	 * 
	 * CAN ONLY HANDLE AMS WITH 2 COMPONENETS!
	 */
	private void sortSegmented2dMAxis(List<Point2d[]> segmented2dMAxis){
		List<Point2d[]> sortedSegmented2dMAxis = new ArrayList<>(2);
		List<Integer> sortedSegmentIds = new ArrayList<>(2);
		int firstSegment = -1;
		int lastSegment = -1;
		System.out.println("AC4234892: SPECIALENDCOMP: " + ams.getSpecialEndComp());
		if(ams.getSpecialEndComp()==1) {
			firstSegment=1;
			lastSegment=0;
		} else {
			firstSegment=0;
			lastSegment=1;
		}
		sortedSegmented2dMAxis.add(segmented2dMAxis.get(firstSegment));
		sortedSegmentIds.add(firstSegment+1);
		sortedSegmented2dMAxis.add(segmented2dMAxis.get(lastSegment));
		sortedSegmentIds.add(lastSegment+1);
		
		
		//TODO: WE NEED TO SORT THE SEGMENTS THEMSELVES
//		System.out.println("AC:00000" + sortedSegmented2dMAxis.get(0)[51]);
//		System.out.println("AC:00000" + sortedSegmented2dMAxis.get(0)[1]);
//		System.out.println("AC:11111" + sortedSegmented2dMAxis.get(1)[1]);
//		System.out.println("AC:11111" + sortedSegmented2dMAxis.get(1)[51]);
		if(!checkConnected(sortedSegmented2dMAxis.get(0), sortedSegmented2dMAxis.get(1))) {
			sortedSegmented2dMAxis = orientTwoMAxes(sortedSegmented2dMAxis);
		}
		
		
		
		this.sortedSegmentIds = sortedSegmentIds;
		this.sortedSegmented2dMAxis = sortedSegmented2dMAxis;
	}
	
	/**
	 * 
	 * @param MAxes - size should be 2
	 * @return
	 */
	private List<Point2d[]> orientTwoMAxes(List<Point2d[]> MAxes){
		double epsilon = 0.00001;
		List<Point2d[]> orientedMAxes = new LinkedList<>();
		
		List<Point2d> axis1Ends = new LinkedList<Point2d>();
		List<Point2d> axis2Ends = new LinkedList<Point2d>();
		
		System.out.println("AC: segment length = " + (MAxes.get(0).length-1));
		axis1Ends.add(MAxes.get(0)[0]);
		axis1Ends.add(MAxes.get(0)[MAxes.get(0).length-1]);
		axis2Ends.add(MAxes.get(1)[0]);
		axis2Ends.add(MAxes.get(1)[MAxes.get(1).length-1]);
		
		System.out.println("AC:00000" + axis1Ends.get(0));
		System.out.println("AC:00000" + axis1Ends.get(1));
		System.out.println("AC:11111" + axis2Ends.get(0));
		System.out.println("AC:11111" + axis2Ends.get(1));
		
		Point2d alignedPt = new Point2d();
		for(Point2d end1: axis1Ends) {
			for(Point2d end2:axis2Ends) {
				if (end1.epsilonEquals(end2,epsilon)) {
					alignedPt = end1;
				}
			}
		}
		System.out.println("AC:15151" + alignedPt);
		
		if(MAxes.get(0)[0].epsilonEquals(alignedPt, epsilon)) {
			System.out.println("FIRST REVERSE CALLED");
			orientedMAxes.add(reversePointsArray(MAxes.get(0)));
		}
		else {
			orientedMAxes.add(MAxes.get(0));
		}
		
		if(!MAxes.get(1)[0].epsilonEquals(alignedPt, epsilon)) {
			System.out.println("SECOND REVERSE CALLEd");
			orientedMAxes.add(reversePointsArray(MAxes.get(1)));
//			System.out.println("AC:191919"+reversePointsArray(MAxes.get(1))[50]);
		} else {
			orientedMAxes.add(MAxes.get(1));
		}
		
//		System.out.println("AC:22222" + orientedMAxes.get(0)[0]);
//		System.out.println("AC:22222" + orientedMAxes.get(0)[50]);
//		System.out.println("AC:33333" + orientedMAxes.get(1)[0]);
//		System.out.println("AC:33333" + orientedMAxes.get(1)[50]);
//		
		return orientedMAxes;
	}

	private static Point2d[] reversePointsArray(Point2d[] points) {
		List<Point2d> pointsAsList = Arrays.asList(points);
		Collections.reverse(pointsAsList);
		Point2d[] reversedPoints = new Point2d[pointsAsList.size()];
		pointsAsList.toArray(reversedPoints);
		return reversedPoints;
	}
	
	private boolean checkConnected(Point2d[] first, Point2d[] second) {
		return first[first.length-1] == second[0];
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
		int numSamples = 255;
		List<Point3d[]> segmented3dMAxis = new LinkedList<>();
		for(int i=1; i<=ams.getNComponent(); i++) {
			Point3d[] points = ams.getTubeComp(i).getmAxisInfo().constructUpSampledMpts(numSamples);
				
			//Removing 0th element which is null
			Point3d[] newPoints = new Point3d[points.length-1];
			for(int j=0; j<points.length-1; j++) {
				newPoints[j] = points[j+1];
			}
			
			segmented3dMAxis.add(newPoints);
		}
		return segmented3dMAxis;
	}

	public AllenMatchStick getAms() {
		return ams;
	}

	public void setAms(AllenMatchStick ams) {
		this.ams = ams;
	}
	
	/**
	 * Between 0 and n, with n being the number of limbs. (In this case, 2)
	 * Finds closest medial axis location to the center of the triangle. 
	 * @param triangleVertices
	 * @return
	 */
	private double calculateNormalizedPositionofTriangle_targetLimbOnly(Point3d[] triangleVertices, int id, double scale) {
		Point2d triangleCenter = new Point2d();
		double xSum = triangleVertices[0].getX()+triangleVertices[1].getX()+triangleVertices[2].getX();
		double ySum = triangleVertices[0].getY()+triangleVertices[1].getY()+triangleVertices[2].getY();
		
		triangleCenter.setX(xSum/3/scale);
		triangleCenter.setY(ySum/3/scale);

		List<Double> distances = new LinkedList<>();
		Point2d[] targetSegment = sortedSegmented2dMAxis.get(sortedSegmentIds.indexOf(id));

		for(Point2d[] axis: sortedSegmented2dMAxis) {
			if(axis.equals(targetSegment)) {
				for(int i=0; i<targetSegment.length;i++) {
					distances.add(triangleCenter.distance(targetSegment[i]));
				}
			}
			//Not target segment, add NaN so it won't be an answer
			else {
				for(int i=0; i<axis.length; i++) {
					distances.add(1000.0);
				}
			}
		}

		int minDistanceIndx = distances.indexOf(Collections.min(distances));


		//TODO: proper normalized position here. with n=1, being the junction, n=2 being end of special Comp.
		double normalizedPosition = normalizedPositions.get(minDistanceIndx); 
//		System.out.println("ACNORM: " + normalizedPosition);
		return normalizedPosition;

	}

}
