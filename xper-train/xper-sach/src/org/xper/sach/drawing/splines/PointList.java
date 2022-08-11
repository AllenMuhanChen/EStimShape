package org.xper.sach.drawing.splines;

//import java.awt.Color;
import java.awt.Graphics;


public class PointList {

	public MyPoint pt[];							// list of control points
	int num;								// # of control points
	int rColor,gColor,bColor; 				// color
	boolean showLine;
	int curPt;
	final int MAXCNTL = 100;				// max # of control points allowed
	final double range = 5;					// pixel(?) range for selecting a control point (this should actually depend on the screen size)

	PointList() {
		num = 0;
		curPt = -1;
		pt = new MyPoint[MAXCNTL];
		rColor = 0;	//(int)(Math.random() * 255);
		gColor = 0;	//(int)(Math.random() * 255);
		bColor = 0;	//(int)(Math.random() * 255);
	}

	public boolean addPoint(double x, double y) {
		if (num == MAXCNTL) return false;
		pt[num] = new MyPoint(x,y);
		num++;
		return true;
	}

	public void changePoint(double x, double y) {
		pt[num-1].x = x;
		pt[num-1].y = y;
	}

	public void changeModPoint(double x, double y) {
		pt[curPt].x = x;
		pt[curPt].y = y;
	}

	public boolean createFinal() {
		return true;
	}

	public boolean done() {
		return true;
	}

	public void setShow(boolean show) {
		showLine = show;
	}

	public int inRegion(double x, double y) {
		int i;
		for (i=0; i<num; i++) {
			if (Math.abs(pt[i].x-x) < range && Math.abs(pt[i].y-y) < range) {
				curPt = i;
				return i;
			}
		}
		curPt = -1;
		return -1;
	}

	public void draw(Graphics g) {
		int i;
		int l = 3;																		// length of crosses
		for (i=0; i< num-1; i++) {
			
			// actually I think I want to replace these with glVertex2f calls 
			// i.e. GL11.glVertex2f(x[i],y[i]);
			// ***casting double to int here, will screw things up for smaller x,y, values***
			g.drawLine((int)pt[i].x-l, (int)pt[i].y, (int)pt[i].x+l, (int)pt[i].y);		// draw a cross at each control point
			g.drawLine((int)pt[i].x, (int)pt[i].y-l, (int)pt[i].x, (int)pt[i].y+l);
			drawDashLine(g, (int)pt[i].x,(int)pt[i].y,(int)pt[i+1].x,(int)pt[i+1].y);   //Draw segment
		}
		g.drawLine((int)pt[i].x-l, (int)pt[i].y, (int)pt[i].x+l, (int)pt[i].y);		// draw next control point
		g.drawLine((int)pt[i].x, (int)pt[i].y-l, (int)pt[i].x, (int)pt[i].y+l);
	}
	


	// draw dash lines
	protected void drawDashLine(Graphics g, int x1, int y1, int x2, int y2) {
		final float seg = 8;
		double x, y;

		if (x1 == x2) {
			if (y1 > y2) {
				int tmp = y1;
				y1 = y2;
				y2 = tmp;
			}
			y = (double)y1;
			while (y < y2) {
				double y0 = Math.min(y+seg, (double)y2);
				g.drawLine(x1, (int)y, x2, (int)y0);
				y = y0 + seg;
			}
			return;
		}
		else if (x1 > x2) {
			int tmp = x1;
			x1 = x2;
			x2 = tmp;
			tmp = y1;
			y1 = y2;
			y2 = tmp;
		}
		double ratio = 1.0*(y2-y1)/(x2-x1);
		double ang = Math.atan(ratio);
		double xinc = seg * Math.cos(ang);
		double yinc = seg * Math.sin(ang);
		x = (double)x1;
		y = (double)y1;

		while ( x <= x2 ) {
			double x0 = x + xinc;
			double y0 = y + yinc;
			if (x0 > x2) {
				x0 = x2;
				y0  = y + ratio*(x2-x);
			}
			g.drawLine((int)x, (int)y, (int)x0, (int)y0);
			x = x0 + xinc;
			y = y0 + yinc;
		}
	}
}






