package org.xper.drawing.renderer;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.Drawable;

public abstract class AbstractRenderer implements Renderer {

	/**
	 * in mm
	 */
	@Dependency
	double width;
	@Dependency
	double height;
	@Dependency
	double depth;

	/**
	 * Distance between monkey and monitor. in mm
	 */
	@Dependency
	double distance;
	@Dependency
	double pupilDistance;
	
	int widthInPixel;
	int heightInPixel;

	/**
	 * coordinate system in mm
	 */ 
	double xmin, xmax, ymin, ymax, zmin, zmax;
	/** 
	 * viewport width and height
	 */
	int vpWidth, vpHeight;
	double vpWidthmm, vpHeightmm;
	/**
	 * horiz and vert unit in mm/pixel
	 */ 
	double hunit, vunit;
	static final double PROJECTION_NEAR = 10.0;

	/**
	 * Convert distance in mm to angle in degree.
	 * 
	 * @param mm
	 * @return
	 */
	public double mm2deg(double mm) {
		return Math.atan(mm / distance) * 180.0 / Math.PI;
	}

	public double deg2mm(double deg) {
		return Math.tan(deg * Math.PI / 180.0) * distance;
	}

	/**
	 * Convert rectangle from mm to pixel.
	 * 
	 * @param mm
	 * @return
	 */
	public Coordinates2D mm2pixel(Coordinates2D mm) {
		double px = mm.getX() / hunit;
		double py = mm.getY() / vunit;
		return new Coordinates2D(px, py);
	}

	/**
	 * Convert rectangle from pixel to mm.
	 * 
	 * @param pixel
	 * @return
	 */
	public Coordinates2D pixel2mm(Coordinates2D pixel) {
		double mx = pixel.getX() * hunit;
		double my = pixel.getY() * vunit;
		return new Coordinates2D(mx, my);
	}

	/**
	 * Convert from window coordinate to world coordinate.
	 * 
	 * window coord: (0, 0) is upper left corner, x rightward increase, y
	 * downward increase
	 * 
	 * @param p
	 * @return
	 */
	public Coordinates2D pixel2coord(Coordinates2D p) {
		double cx = (xmax - xmin) / (vpWidth - 1.0) * p.getX() + xmin;
		double cy = (ymin - ymax) / (vpHeight - 1.0) * p.getY() + ymax;
		return new Coordinates2D(cx, cy);
	}

	/**
	 * Convert from world coordinate to window coordinate.
	 * 
	 * window coord: (0, 0) is upper left corner, x rightward increase, y
	 * downward increase
	 * 
	 * @param c
	 * @return
	 */
	public Coordinates2D coord2pixel(Coordinates2D c) {
		double px = (c.getX() - xmin) * (vpWidth - 1.0) / (xmax - xmin);
		double py = (c.getY() - ymax) * (vpHeight - 1.0) / (ymin - ymax);
		return new Coordinates2D(px, py);
	}

	/**
	 * Convert from world coordinate to viewport coordinate.
	 * 
	 * viewport coord: (0, 0) is lower left corner, rightward, upward increase
	 * 
	 * @param c
	 * @return
	 */
	public Coordinates2D coord2vp(Coordinates2D c) {
		double px = (c.getX() - xmin) * (vpWidth - 1.0) / (xmax - xmin);
		double py = (c.getY() - ymin) * (vpHeight - 1.0) / (ymax - ymin);
		return new Coordinates2D(px, py);
	};

	/**
	 * Convert from viewport coordinate to world coordinate.
	 * 
	 * viewport coord: (0, 0) is lower left corner, rightward, upward increase
	 * 
	 * @param p
	 * @return
	 */
	public Coordinates2D vp2coord(Coordinates2D p) {
		double cx = (xmax - xmin) / (vpWidth - 1.0) * p.getX() + xmin;
		double cy = (ymax - ymin) / (vpHeight - 1.0) * p.getY() + ymin;
		return new Coordinates2D(cx, cy);
	}

	/**
	 * Convert from world coordinate to normalized coordinate.
	 * 
	 * normalized coordinated: [0,1][0,1]
	 * 
	 * @param c
	 * @return
	 */
	public Coordinates2D coord2norm(Coordinates2D c) {
		double nx = (c.getX() - xmin) / (xmax - xmin);
		double ny = (c.getY() - ymin) / (ymax - ymin);
		return new Coordinates2D(nx, ny);
	}

	/**
	 * Convert from normalized coordinate to world coordinate.
	 * 
	 * normalized coordinated: [0,1][0,1]
	 * 
	 * @param n
	 * @return
	 */
	public Coordinates2D norm2coord(Coordinates2D n) {
		double cx = n.getX() * (xmax - xmin) + xmin;
		double cy = n.getY() * (ymax - ymin) + ymin;
		return new Coordinates2D(cx, cy);
	}

	public void init() {
		calculateCoordinates();
		GL11.glViewport(0, 0, vpWidth, vpHeight);
	}

	/**
	 * This is called in the Open GL thread instead of in the application context.
	 */
	public void init(int w, int h) {
		widthInPixel = w;
		heightInPixel = h;
		init();
	}

	public void draw(Drawable scene, Context context) {
		context.setViewportIndex(0);
		context.setRenderer(this);
		scene.draw(context);
	}

	protected void calculateCoordinates() {
		hunit = width / (double) widthInPixel;
		vunit = height / (double) heightInPixel;

		// coordinate in actual measurement
		xmin = -width / 2.0 + hunit / 2.0;
		// max visible point; actual max coord is xmax + hunit
		xmax = width / 2.0 - hunit / 2.0;

		ymin = -height / 2.0 + vunit / 2.0;
		ymax = height / 2.0 - vunit / 2.0;

		zmax = distance - PROJECTION_NEAR;
		zmin = -depth;

		vpWidth = widthInPixel;
		vpHeight = heightInPixel;
		vpWidthmm = width;
		vpHeightmm = height;
	}

	public double getDepth() {
		return depth;
	}

	public void setDepth(double depth) {
		this.depth = depth;
	}

	public double getDistance() {
		return distance;
	}

	public void setDistance(double distance) {
		this.distance = distance;
	}

	public double getHeight() {
		return height;
	}

	public void setHeight(double height) {
		this.height = height;
	}

	public double getPupilDistance() {
		return pupilDistance;
	}

	public void setPupilDistance(double pupilDistance) {
		this.pupilDistance = pupilDistance;
	}

	public double getWidth() {
		return width;
	}

	public void setWidth(double width) {
		this.width = width;
	}

	public double getHunit() {
		return hunit;
	}

	public int getVpHeight() {
		return vpHeight;
	}

	public double getVpHeightmm() {
		return vpHeightmm;
	}

	public int getVpWidth() {
		return vpWidth;
	}

	public double getVpWidthmm() {
		return vpWidthmm;
	}

	public double getVunit() {
		return vunit;
	}

	public double getXmax() {
		return xmax;
	}

	public double getXmin() {
		return xmin;
	}

	public double getYmax() {
		return ymax;
	}

	public double getYmin() {
		return ymin;
	}

	public double getZmax() {
		return zmax;
	}

	public double getZmin() {
		return zmin;
	}

}
