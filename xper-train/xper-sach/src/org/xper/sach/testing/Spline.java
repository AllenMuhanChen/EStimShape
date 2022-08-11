package org.xper.sach.testing;

import java.awt.Graphics;
import java.awt.Color;
import java.awt.Event;

import java.applet.Applet;

public class Spline extends Applet {
   private static final long serialVersionUID = 1L;
   
   Point[] points;   //points to be interpolated
   Point[] control;   //control points
   int numpoints;
   double t;   //time variable
   static final double k = .05; //partition length
   int moveflag;   //point movement

   //this method initializes the applet
   
   public void init() {
      //start off with 6 points
      points = new Point[6];
      control = new Point[6];
      numpoints = 6;
      moveflag = numpoints;
      int increment = (int)((getWidth()-60)/(numpoints-1));
      for(int i=0;i<numpoints;i++) {
         points[i] = new Point((i*increment)+30,(int)(getHeight()/2));
      }
      System.out.println("init done");

   }
   
   //this method is called by the repaint() method
   public void update(Graphics g) {
      paint(g);
   }
   
   public void paint(Graphics g) {
      //points to be plotted
      double x1,y1,x2,y2;
      //Clear screen and set colors
      setBackground(Color.white);
      g.setColor(Color.white);
      g.fillRect(0,0,getWidth(),getHeight());
      g.setColor(Color.black);

      
      //Change interpolating points into control points
      control[0] = new Point(points[0].x,points[0].y);												// set 1st ctlPt
      control[numpoints-1] = new Point(points[numpoints-1].x,points[numpoints-1].y);				// set last ctlPt
      
      x1= 1.6077*points[1].x - .26794 * points[0].x - .43062 * points[2].x + .11483 * points[3].x - .028708 * points[4].x + .004785*points[5].x;
      y1= 1.6077*points[1].y - .26794 * points[0].y - .43062 * points[2].y + .11483 * points[3].y - .028708 * points[4].y + .004785*points[5].y;
      control[1] = new Point(x1,y1);
      
      x1= -.43062 * points[1].x + .07177 * points[0].x + 1.7225 * points[2].x - .45933 * points[3].x + .11483 * points[4].x - .019139 * points[3].x;
      y1= -.43062 * points[1].y + .07177 * points[0].y + 1.7225 * points[2].y - .45933 * points[3].y + .11483 * points[4].y - .019139 * points[3].y;
      control[2] = new Point(x1,y1);
      
      x1= .11483 * points[1].x - .019139 * points[0].x - .45933 * points[2].x + 1.7225 * points[3].x - .43062 * points[4].x + .07177 * points[5].x;
      y1= .11483 * points[1].y - .019139 * points[0].y - .45933 * points[2].y + 1.7225 * points[3].y - .43062 * points[4].y + .07177 * points[5].y;
      control[3] = new Point(x1,y1);
      
      x1=- .028708 * points[1].x + .004785 * points[0].x + .114835 * points[2].x - .43062 * points[3].x + 1.6077 * points[4].x - .26794 * points[5].x;
      y1=- .028708 * points[1].y + .004785 * points[0].y + .114835 * points[2].y - .43062 * points[3].y + 1.6077 * points[4].y - .26794 * points[5].y;
      control[4] = new Point(x1,y1);
      
      //Plot points
      for(int i=0;i<numpoints;i++)
         g.fillOval((int)points[i].x-2,(int)points[i].y-2,4,4);

      //draw n bezier curves using Bernstein Polynomials
      x1=points[0].x;
      y1=points[0].y;
      for(int i=1;i<numpoints;i++) {
         for(t=i-1;t<=i;t+=k) {
            double tValue = (t-(i-1));
            x2= points[i-1].x + tValue * (-3*points[i-1].x + 3 * (.6667 * control[i-1].x + .3333 * control[i].x) + tValue * (3 * points[i-1].x - 6 * (.6667 * control[i-1].x + .3333 * control[i].x) + 3 * (.3333 * control[i-1].x + .6667*control[i].x) + (-points[i-1].x + 3 * (.6667 * control[i-1].x + .3333 * control[i].x) - 3 * (.3333 * control[i-1].x + .6667 * control[i].x) + points[i].x) * tValue));
            y2= points[i-1].y + tValue * (-3*points[i-1].y + 3 * (.6667 * control[i-1].y + .3333 * control[i].y) + tValue * (3 * points[i-1].y - 6 * (.6667 * control[i-1].y + .3333 * control[i].y) + 3 * (.3333 * control[i-1].y + .6667*control[i].y) + (-points[i-1].y + 3 * (.6667 * control[i-1].y + .3333 * control[i].y) - 3 * (.3333 * control[i-1].y + .6667 * control[i].y) + points[i].y) * tValue));
            
            g.drawLine((int)x1,(int)y1,(int)x2,(int)y2);
            x1=x2;
            y1=y2;
         }
         //System.out.print("b");
      }

   }
   

   //Check if user has clicked on point
   public boolean mouseDown(Event evt, int x, int y) {
      Point p = new Point(x,y);
      for(int i=0;i<numpoints;i++) {
         for(int j=-8;j<15;j++) {
            for(int l=-8;l<15;l++) {
               if(p.equals(new Point(points[i].x+j, points[i].y+l))) {
                  //set moveflag to the ith point
                  moveflag=i;
               }
                  
            }
         }
      }
      return true;
   }
   public boolean mouseDrag(Event evt, int x, int y) {
      //check if user is trying to drag an old point
      if(moveflag < numpoints) {
         //move the point and redraw screen
         points[moveflag].move(x,y);
         repaint();
      }
      return true;
   }
      //if user unclicks mouse, reset moveflag
   public boolean mouseUp(Event evt, int x, int y) {
      moveflag = 6;
      return true;
   }
}
class Point {
   double x, y;
   Point(double newX, double newY) {
      x = newX;
      y = newY;
   }
   void move(double moveX, double moveY) {
      x = moveX;
      y = moveY;
   }
   public boolean equals(Point p) {
      if ((int)p.x == (int)x && (int)p.y == (int)y) return true;
      return false;
   }
}