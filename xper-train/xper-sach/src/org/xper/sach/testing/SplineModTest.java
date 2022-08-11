package org.xper.sach.testing;

/*
bezier.java         by Gengbin Zheng
 */

import java.awt.*;
import java.applet.*;

import org.xper.sach.drawing.splines.BezierLine;
import org.xper.sach.drawing.splines.BsplineLine;
import org.xper.sach.drawing.splines.PointList;
import org.xper.sach.util.SachMathUtil;

public class SplineModTest extends Applet {
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
		pts = new PointList[200];
		nline = -1;
		drawing = false;
		action = DRAW_BEZIER;

		errDlg = new ErrorFrame(" Too many points!");
		
		// create b-spline and show it here:
		nline++;
		pts[nline] = new BsplineLine();
		
		int xOffset = 250;
		int yOffset = 200;
		double scaleFactor = 20;
//		
//		
//		LimbObject limb1 = new LimbObject();
//		limb1.init(2,8,0,new double[] {2,-4});
//		//splinePts = limb1.cntlPts;
//		LimbObject limb2 = new LimbObject();
//		limb2.init(2,8,90,new double[] {-4,2});
//		
//		//LimbObject obj = new LimbObject();
//		//obj.init(2,10,90,new double[] {0,0});
//		
//		double[][] myPts = SachMathUtil.mergeArrays(limb1.cntlPts,limb2.cntlPts);

		
		
//		// ***CHANGE THIS***
//		int myPts[] = 	{	   // A BB C DD E FF G HH A BB (only one each for side points)
//				  0,	 5,
//				  1,	 5, 
//				  1,	 5, 
//				  1,	 0, 
//				  1,	-5, 
//				  1,	-5, 
//				  0,	-5, 
//				 -1,	-5, 
//				 -1,	-5, 
//				 -1,	 0, 
//				 -1,	 5, 
//				 -1,	 5,
//				  0,	 5,
//				  1,	 5, 
//				  1,	 5		
//			};
//		
//		for (int n = 0; n < myPts.length; n++) {
//			pts[nline].addPoint((int)(myPts[n][0]*scaleFactor)+xOffset,(int)(myPts[n][1]*scaleFactor)+yOffset);
//		}
//		//pts[nline].addPoint(0,0);	// throwaway! (last point is discarded later)		
//		pts[nline].done();		// creates spline from control points
//		

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
				if (action == DRAW_BEZIER) pts[nline] = new BezierLine();
				if (action == DRAW_BSPLINE) pts[nline] = new BsplineLine();
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

