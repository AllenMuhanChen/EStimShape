package org.xper.allen.nafc.vo;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

public class AllenMorphData {
	boolean removed;
	Vector3d tangent;
	Point3d position;
	double curvature;
	double rotation;
	double length;
	double thickness;
	double juncRad;
	double midRad;
	double endRad;
	
	public AllenMorphData(Vector3d tangent, Point3d position, double curvature, double rotation, double length,
			double thickness, double juncRad, double midRad, double endRad) {
		this.tangent = tangent;
		this.position = position;
		this.curvature = curvature;
		this.rotation = rotation;
		this.length = length;
		this.thickness = thickness;
		this.juncRad = juncRad;
		this.midRad = midRad;
		this.endRad = endRad;
	}
	public Vector3d getTangent() {
		return tangent;
	}
	public void setTangent(Vector3d tangent) {
		this.tangent = tangent;
	}
	public Point3d getPosition() {
		return position;
	}
	public void setPosition(Point3d position) {
		this.position = position;
	}
	public double getCurvature() {
		return curvature;
	}
	public void setCurvature(double curvature) {
		this.curvature = curvature;
	}
	public double getRotation() {
		return rotation;
	}
	public void setRotation(double rotation) {
		this.rotation = rotation;
	}
	public double getLength() {
		return length;
	}
	public void setLength(double length) {
		this.length = length;
	}
	public double getThickness() {
		return thickness;
	}
	public void setThickness(double thickness) {
		this.thickness = thickness;
	}
	public double getJuncRad() {
		return juncRad;
	}
	public void setJuncRad(double juncRad) {
		this.juncRad = juncRad;
	}
	public double getMidRad() {
		return midRad;
	}
	public void setMidRad(double midRad) {
		this.midRad = midRad;
	}
	public double getEndRad() {
		return endRad;
	}
	public void setEndRad(double endRad) {
		this.endRad = endRad;
	}
}
