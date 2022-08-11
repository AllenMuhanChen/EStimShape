package org.xper.sach.testing.splinetest;

/*
bezier.java         by Gengbin Zheng
 */

import java.awt.*;
import java.applet.*;

public class SplineTest extends Applet {
	Button draw1Button, draw2Button, modifyButton, deleteButton, clearButton;
	myCanvas canvas;
	TextField statusBar;

	public void init() {
		GridBagLayout layout = new GridBagLayout();
		setLayout(layout);

		GridBagConstraints constraints = new GridBagConstraints();

		draw1Button = new Button("Draw Bezier");
		draw2Button = new Button("Draw B-Spline");
		modifyButton = new Button("Modify");
		deleteButton = new Button("Delete curve");
		clearButton = new Button("Clear All");

		constraints.fill = GridBagConstraints.BOTH;
		constraints.weightx = 1;
		layout.setConstraints(draw1Button, constraints);
		add(draw1Button);

		layout.setConstraints(draw2Button, constraints);
		add(draw2Button);

		layout.setConstraints(modifyButton, constraints);
		add(modifyButton);

		constraints.gridwidth = GridBagConstraints.RELATIVE;
		layout.setConstraints(deleteButton, constraints);
		add(deleteButton);

		constraints.gridwidth = GridBagConstraints.REMAINDER;
		layout.setConstraints(clearButton, constraints);
		add(clearButton);

		canvas = new myCanvas();
		constraints.weighty = 1;
		layout.setConstraints(canvas, constraints);
		add(canvas);

		statusBar = new TextField("Draw Bezier: click to add a point, double click to finish drawing", 45);
		statusBar.setEditable(false);

		constraints.weighty = 0;
		layout.setConstraints(statusBar, constraints);
		add(statusBar);

		resize(550,450);              //Set window size
	}

	public boolean action(Event evt, Object arg) {
		if (evt.target instanceof Button) 
			HandleButtons(arg);

		return true; 
	}

	protected void HandleButtons(Object label) {
		String helpMsg;

		if (label == "Clear All")
			helpMsg = "All curves are cleared.";
		else if (label == "Draw Bezier")
			helpMsg = "Draw Bezier: click to add a point, double click to finish drawing"; 
		else if (label == "Draw B-Spline")
			helpMsg = "Draw B-Spline: click to add a point, double click to finish drawing.";
		else if (label == "Modify")
			helpMsg = "Modify: select a control point, drag mouse to modify and release to finish.";
		else if (label == "Delete curve")
			helpMsg = "Delete: select a curve, click to delete.";
		else
			helpMsg = "";

		statusBar.setText(helpMsg);
		canvas.HandleButtons(label);
	}
}

class myCanvas extends Canvas {
	PointList pts[];
	int nline;
	int curObj;
	boolean drawing;  
	int action;
	final int DRAW_BEZIER=1, DRAW_BSPLINE=2, MODIFY=3, DELETE=4;
	ErrorFrame errDlg;
	// double buffering
	Image img = null;
	Graphics backg;

	public myCanvas() {
		
		// this is for testing:
		pts = new PointList[200];
		nline = -1;
		drawing = false;
		action = DRAW_BEZIER;

		errDlg = new ErrorFrame(" Too many points!");
		
		// create b-spline and show it here:
		nline++;
		pts[nline] = new bspline();

		int xOffset = 250;
		int yOffset = 200;
		double scaleFactor = 2;
		
		int myPts[] = {	0,-50, -50,-50, -50,-35, -8,-35, -8,50, 8,50, 8,-35, 
						50,-35, 50,-50, 0,-50, -50,-50, -50,-35 };
		
		for (int n = 0; n < myPts.length-1; n=n+2) {
			pts[nline].addPoint((int)(myPts[n]*scaleFactor)+xOffset,(int)(myPts[n+1]*scaleFactor)+yOffset);
		}

		pts[nline].addPoint(0,0);	// throwaway!
		
		pts[nline].done();

		
		
	}

	void setcursor(boolean working) {
		Cursor curs;
		if (working) 
			curs = new Cursor(Cursor.HAND_CURSOR);
		else
			curs = new Cursor(Cursor.DEFAULT_CURSOR);
		setCursor(curs);
	}

	public boolean mouseUp(Event evt, int x, int y) {
		if (action == DRAW_BEZIER || action == DRAW_BSPLINE) {
			if (drawing) {
				if (!pts[nline].addPoint(x,y)) {
					if (!errDlg.isShowing()) errDlg.show();
					drawing = false;
					nline --;
					setcursor(drawing);
				}
			}
			repaint();
		} 
		if (action == MODIFY) {
			if (drawing) {
				drawing = false;
				setcursor(drawing);
			}
		}
		if (action == DELETE) {
			if (curObj != -1) {
				for (int i=curObj; i< nline; i++) pts[i] = pts[i+1];
				nline--;
				repaint();
			}
		}
		return true;
	}

	public boolean mouseDown(Event evt, int x, int y)
	{
		if (action == DRAW_BEZIER || action == DRAW_BSPLINE) {
			if (drawing == false) {
				nline ++;
				if (action == DRAW_BEZIER) pts[nline] = new bezierLine();
				if (action == DRAW_BSPLINE) pts[nline] = new bspline();
				pts[nline].addPoint(x,y);
				drawing = true;
				setcursor(drawing);
			}
			else {
				if (evt.clickCount == 2) {
					if (!pts[nline].done()) {
						if (!errDlg.isShowing()) errDlg.show();
						nline --;
					}
					drawing = false;
					setcursor(drawing);
				}
			}
		}
		if (action == MODIFY) {
			if (curObj != -1) {
				drawing = true;
				setcursor(drawing);
			}
		}
		return true;
	}

	public boolean mouseMove(Event evt, int x, int y)
	{
		if (action == DRAW_BEZIER || action == DRAW_BSPLINE) {
			if (drawing) {
				pts[nline].changePoint(x,y);
				repaint();
			}
		}
		if (action == MODIFY || action == DELETE) {
			if (drawing == false) {
				int oldObj = curObj;
				curObj = -1;
				for (int i=0; i<=nline; i++) {
					if (pts[i].inRegion(x,y) != -1) {
						curObj = i;
						break; 
					}
				}
				if (oldObj != curObj) repaint();
			}
		}
		return true;
	}

	public boolean mouseDrag(Event evt, int x, int y)
	{
		if (action == MODIFY) {
			if (drawing == true)  {
				pts[curObj].changeModPoint(x,y);
				if (!pts[curObj].createFinal()) {
					if (!errDlg.isShowing()) errDlg.show();
					nline --;
				}
				repaint();
			}
		}
		return true;
	}

	public void HandleButtons(Object label) {
		if (drawing) {
			drawing = false;
			setcursor(drawing);
		}
		if (label == "Clear All") {
			nline = -1;
			repaint();
			return;
		}
		if (action == DRAW_BEZIER || action == DRAW_BSPLINE) {
			if (drawing) pts[nline].done();
		}

		if (label == "Draw Bezier") {
			action = DRAW_BEZIER;
			for (int i=0; i<=nline; i++)
				pts[i].setShow(false);
			repaint();
		}
		else if (label == "Draw B-Spline") {
			action = DRAW_BSPLINE;
			for (int i=0; i<=nline; i++)
				pts[i].setShow(false);
			repaint();
		}
		else if (label == "Modify") {
			action = MODIFY;
			for (int i=0; i<=nline; i++)
				pts[i].setShow(true);
			repaint();
		}
		else if (label == "Delete curve") {
			action = DELETE;
			for (int i=0; i<=nline; i++)
				pts[i].setShow(true);
			repaint();
		}
	}

	public void paint(Graphics g) {
		update(g);
	}

	public void update(Graphics g) {    //Don't bother
		int i,n;
		Dimension d=size();

		if (img == null) {
			img = createImage(d.width, d.height);
			backg = img.getGraphics();
		}

		backg.setColor(new Color(204,204,204));    	//Set color for background
		backg.fillRect(0,0, d.width, d.height);		//Draw Backround

		// draw border
		backg.setColor(new Color(0,0,0));
		backg.drawRect(1,1,d.width-3,d.height-3);

		for (n=0; n <= nline; n++)
			pts[n].draw(backg);

		g.drawImage(img, 0, 0, this);
	}
}

class ErrorFrame extends Frame {
	Label label;
	Button button;
	String errMsg;

	ErrorFrame(String msg) {
		super("Error!");
		errMsg = msg;

		BorderLayout layout = new BorderLayout();
		setLayout(layout);

		label = new Label(errMsg);
		add("North", label);

		button = new Button("Ok");
		add("South", button);

		resize(200,100);
	}

	public boolean action(Event evt, Object arg) {
		if (arg == "Ok")
			dispose();
		return true;
	}
}

class PointList {
	Point pt[];
	int num;
	int rColor,gColor,bColor; 	// color
	boolean showLine;
	int curPt;
	final int MAXCNTL = 50;
	final int range = 5;

	PointList() {
		num = 0;
		curPt = -1;
		pt = new Point[MAXCNTL];
//		rColor = (int)(Math.random() * 255);
//		gColor = (int)(Math.random() * 255);
//		bColor = (int)(Math.random() * 255);
		rColor = 0;
		gColor = 0;
		bColor = 0;
	}

	boolean addPoint(int x, int y) {
		if (num == MAXCNTL) return false;
		pt[num] = new Point(x,y);
		num++;
		return true;
	}

	void changePoint(int x, int y) {
		pt[num-1].x = x;
		pt[num-1].y = y;
	}

	void changeModPoint(int x, int y) {
		pt[curPt].x = x;
		pt[curPt].y = y;
	}

	boolean createFinal() {
		return true;
	}

	boolean done() {
		return true;
	}

	void setShow(boolean show) {
		showLine = show;
	}

	int inRegion(int x, int y) {
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

	void draw(Graphics g) {
		int i;
		int l = 3;
		for (i=0; i< num-1; i++) {
			g.drawLine(pt[i].x-l, pt[i].y, pt[i].x+l, pt[i].y);
			g.drawLine(pt[i].x, pt[i].y-l, pt[i].x, pt[i].y+l);
			drawDashLine(g, pt[i].x,pt[i].y,pt[i+1].x,pt[i+1].y);   //Draw segment
		}
		g.drawLine(pt[i].x-l, pt[i].y, pt[i].x+l, pt[i].y);
		g.drawLine(pt[i].x, pt[i].y-l, pt[i].x, pt[i].y+l);
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
} // end: PointList


class bezierLine extends PointList {
	Point bpt[];
	int bnum;
	boolean ready;
	final int MAXPOINT = 1800;
	final int ENOUGH = 2;
	final int RECURSION = 900;
	int nPointAlloc;
	int enough;		// control how well we draw the curve.
	int nRecur;		// counter of number of recursion
	Point buffer[][];
	int nBuf, nBufAlloc;

	bezierLine() {
		bpt = new Point[MAXPOINT];
		nPointAlloc = MAXPOINT;
		bnum = 0;
		enough = ENOUGH;
		showLine = true;
		ready = false;
		buffer = null;
	}

	protected int distance(Point p0,Point p1,Point p2)
	{
		int a,b,y1,x1,d1,d2;

		if(p1.x==p2.x && p1.y==p2.y) return Math.min(Math.abs(p0.x-p1.x),Math.abs(p0.y-p1.y));
		a=p2.x-p1.x;    b=p2.y-p1.y;
		y1=b*(p0.x-p1.x)+a*p1.y;
		x1=a*(p0.y-p1.y)+b*p1.x;
		d1=Math.abs(y1-a*p0.y);
		d2=Math.abs(x1-b*p0.x);
		if (a==0) return Math.abs(d2/b);
		if (b==0) return Math.abs(d1/a);
		return Math.min(Math.abs(d1/a),Math.abs(d2/b));
	}

	protected void curve_split(Point p[],Point q[],Point r[],int num)
	{
		int i,j;

		//      for (i=0;i<num;i++) q[i] = new Point(p[i]);
		for (i=0;i<num;i++) q[i].copy(p[i]);
		for (i=1;i<=num-1;i++) {
			//         r[num-i] = new Point(q[num-1]);
			r[num-i].copy(q[num-1]);
			for (j=num-1;j>=i;j--) {
				//	    q[j] = new Point((q[j-1].x+q[j].x)/2, (q[j-1].y+q[j].y)/2);
				q[j].x = (q[j-1].x+q[j].x)/2;
				q[j].y = (q[j-1].y+q[j].y)/2;
			}
		}
		//      r[0] = new Point(q[num-1]);
		r[0].copy(q[num-1]);
	}

	// reuse buffer
	private Point get_buf(int num)[] {
		Point b[];
		if (buffer == null) {
			buffer = new Point[500][num];
			nBufAlloc = 500;
			nBuf = 0;
		}
		if (nBuf == 0) {
			b = new Point[num];
			for (int i=0; i< num; i++) b[i] = new Point();
			return b;
		}
		else {
			nBuf --;
			b = buffer[nBuf];
			return b;
		}
	}

	private void put_buf(Point b[]) {
		if (nBuf >= nBufAlloc) {
			Point newBuf[][] = new Point[nBufAlloc + 500][num];
			for (int i=0; i<nBuf; i++) newBuf[i] = buffer[i];
			nBufAlloc += 500;
			buffer = newBuf;
		}
		buffer[nBuf] = b;
		nBuf++;
	}

	protected boolean bezier_generation(Point pt[], int num, Point result[], int n[]) {
		Point qt[],rt[];	// for split
		int d[],i,max;

		nRecur++;
		if (nRecur > RECURSION) return false;

		d = new int[MAXCNTL];
		for (i=1;i<num-1;i++) d[i]=distance(pt[i],pt[0],pt[num-1]);
		max=d[1];
		for (i=2;i<num-1;i++) if (d[i]>max) max=d[i];
		if (max <= enough || nRecur > RECURSION) {
			if (n[0]==0) {
				if (bnum > 0) 
					result[0].copy(pt[0]);
				else
					result[0] = new Point(pt[0]);
				n[0]=1;
			}
			//reuse
			if (bnum > n[0])
				result[n[0]].copy(pt[num-1]);
			else
				result[n[0]] = new Point(pt[num-1]);
			n[0]++;
			if (n[0] == MAXPOINT-1) return false;
		}
		else {
			//	   qt = new Point[num];
			//	   rt = new Point[num];
			qt = get_buf(num);
			rt = get_buf(num);
			curve_split(pt,qt,rt,num);
			if (!bezier_generation(qt,num,result,n)) return false;
			put_buf(qt);
			if (!bezier_generation(rt,num,result,n)) return false;
			put_buf(rt);
		}
		return true;
	}

	public boolean try_bezier_generation(Point pt[], int num, Point result[], int n[])
	{
		int oldN = n[0];

		if (enough == ENOUGH && num > 6) enough += 3;
		//       if (enough > ENOUGH) enough -= 5;
		nRecur = 0;
		// in case of recursion stack overflow, relax "enough" and keep trying
		while (!bezier_generation(pt, num, bpt, n))
		{
			n[0] = oldN;
			enough += 5;
			nRecur = 0;
		}
		return true;
	}

	boolean createFinal()
	{
		int n[];
		n = new int[1];
		if (!try_bezier_generation(pt, num, bpt, n)) 
		{
			bnum = 0;
			return false;
		}
		else {
			bnum = n[0];
			return true;
		}
	}

	boolean done()
	{
		num --;
		showLine = false;
		ready = true;
		return createFinal();
	}

	void draw(Graphics g)
	{
		g.setColor(new Color(rColor,gColor,bColor));
		if (showLine)
		{
			super.draw(g);
			if (curPt != -1)
				g.drawRect(pt[curPt].x-range, pt[curPt].y-range, 2*range+1,2*range+1);
		}

		if (ready)
			for (int i=0; i< bnum-1; i++)
			{
				g.drawLine(bpt[i].x,bpt[i].y,bpt[i+1].x,bpt[i+1].y);   
			}
			//System.out.print(".");
	}
}

class bspline extends bezierLine 
{
	protected void bspline_to_Bezier(int j, Point p[], Point v[])
	{
		int h,i;
		double tmp,x1,x2;

		for (h=0;h<=1;h++) {	// this is done 2x (h=0, h=1)
			for (i=0;i<=1;i++)  {	// this is done 2x (i=0, i=1)
				//tmp=1.0*((j+h)-(j-2+h+i))*1.0/((j+1+i+h)-(j-2+h+i));   //  (2-i)/3
				tmp=(2.0-i)/3.0;
				x1=p[j-2+i+h].x;
				x2=p[j-2+i+h-1].x;
				v[2*h+i].x=(int)(tmp*x1+(1.0-tmp)*x2);
				x1=p[j-2+i+h].y;
				x2=p[j-2+i+h-1].y;
				v[2*h+i].y=(int)(tmp*x1+(1.0-tmp)*x2);
			}
			//tmp=1.0*((j+h)-(j-1+h))/((j+1+h)-(j-1+h));    	// 1/2
			tmp=1.0/2.0;
			x1=v[1+2*h].x;
			x2=v[2*h].x;
			v[3*h].x=(int)(tmp*x1+(1.0-tmp)*x2);
			x1=v[1+2*h].y;
			x2=v[2*h].y;
			v[3*h].y=(int)(tmp*x1+(1-tmp)*x2);
		}
	}

	protected boolean bspline_generation(Point pt[],int n,Point result[],int num[])
	{
		Point v[];
		int i,j;

		v = new Point[4];
		for (i=0; i<4; i++) v[i] = new Point();
		for (j=3;j<n;j++) {
			bspline_to_Bezier(j,pt,v);
			if (num[0] > 0) num[0]=num[0]-1;
			if (!try_bezier_generation(v,4,result,num)) return false;
		}
		return true;
	}

	boolean createFinal()
	{
		int n[];
		n = new int[1];
		n[0] = 0;
		if (bspline_generation(pt, num, bpt, n))
		{
			bnum = n[0];
			return true;
		}
		else {
			bnum = 0;
			return false;
		}
	}

}

class Point 
{
	int x,y;

	Point(Point p)
	{
		x = p.x;
		y = p.y;
	}
	Point(int _x, int _y)
	{
		x = _x;
		y = _y;
	}
	Point()
	{
		x = 0;
		y = 0;
	}
	void copy(Point p)
	{
		x = p.x;
		y = p.y;
	}
}

