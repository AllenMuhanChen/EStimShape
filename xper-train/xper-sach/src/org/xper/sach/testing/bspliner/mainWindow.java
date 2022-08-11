package org.xper.sach.testing.bspliner;

import java.awt.*;   
import java.awt.event.*;   
import java.awt.geom.*;   
import java.util.*;   
import javax.swing.*;   
import java.text.*; 

public class mainWindow      
{   
    public static void main(String[] args)    
    {   
        JFrame frame2=new BsplineCurveFrame();   
        MyWindowListener l = new MyWindowListener();   
        frame2.addWindowListener(l);   
        //Text t=new Text();   
        //t.init();   
        //frame2.getContentPane().add(t,BorderLayout.SOUTH);   
        frame2.setVisible(true);   
    }   
}   
class BsplineCurveFrame extends JFrame   
{     
   JLabel jl1,jl2,jl3,jl4,jl5;//,jl6   
   static JTextField jf1,jf2,jf3,jf4,jf5,jf6,jf7,jf8,jf9,jf10;//,jf11,jf12   
      
   public BsplineCurveFrame()   
   {     
      setTitle("some title");   
      setSize(DEFAULT_WIDTH, DEFAULT_HEIGHT);   
   
      final ShapePanel1 panel = new ShapePanel1();   
      add(panel, BorderLayout.CENTER);   
      final JPanel panel2= new JPanel();   
      jl1=new JLabel("P1",JLabel.RIGHT);   
      jl2=new JLabel("P2",JLabel.RIGHT);   
      jl3=new JLabel("P3",JLabel.RIGHT);   
      jl4=new JLabel("P4",JLabel.RIGHT);   
      jl5=new JLabel("P5",JLabel.RIGHT);   
      jf1=new JTextField("-25",10);   
      jf2=new JTextField("-10",10);   
      jf3=new JTextField("-22",10);   
      jf4=new JTextField("14",10);   
      jf5=new JTextField("-12",10);   
      jf6=new JTextField("0",10);   
      jf7=new JTextField("-11",10);   
      jf8=new JTextField("-25",10);   
      jf9=new JTextField("-2",10);   
      jf10=new JTextField("2",10);   
      //jf11=new JTextField(10);   
     // jf12=new JTextField(10);   
      Box box1=Box.createHorizontalBox();   
      box1.add(jl1);   
      box1.add(jf1);   
      box1.add(Box.createHorizontalStrut(15));   
      box1.add(jf2);   
      Box box2=Box.createHorizontalBox();   
      box2.add(jl2);   
      box2.add(jf3);   
      box2.add(Box.createHorizontalStrut(15));   
      box2.add(jf4);   
      Box box3=Box.createHorizontalBox();   
      box3.add(jl3);   
      box3.add(jf5);   
      box3.add(Box.createHorizontalStrut(15));   
      box3.add(jf6);   
      Box box4=Box.createHorizontalBox();   
      box4.add(jl4);   
      box4.add(jf7);   
      box4.add(Box.createHorizontalStrut(15));   
      box4.add(jf8);   
      Box box5=Box.createHorizontalBox();   
      box5.add(jl5);   
      box5.add(jf9);   
      box5.add(Box.createHorizontalStrut(15));   
      box5.add(jf10);   
      //Box box6=Box.createHorizontalBox();   
      //box6.add(jl6);   
      //box6.add(jf11);   
      //box6.add(Box.createHorizontalStrut(15));   
     // box6.add(jf12);   
      Box boxH=Box.createHorizontalBox();   
      boxH.add(box1);   
      boxH.add(Box.createHorizontalStrut(20));   
      boxH.add(box2);   
      Box boxH1=Box.createHorizontalBox();   
      boxH1.add(box3);   
      boxH1.add(Box.createHorizontalStrut(20));   
      boxH1.add(box4);   
      Box boxH2=Box.createHorizontalBox();   
      boxH2.add(box5);   
      boxH2.add(Box.createHorizontalStrut(250));   
      //boxH2.add(box6);   
      Box boxv=Box.createVerticalBox();   
      boxv.add(boxH);   
      boxv.add(boxH1);   
      boxv.add(boxH2);   
      panel2.add(boxv);   
      final JButton button1 = new JButton("start");   
      final JPanel panel3= new JPanel();   
      panel3.add(button1,BorderLayout.CENTER);   
      button1.addActionListener(new   
         ActionListener()   
         {   
   
            public void actionPerformed(ActionEvent event)   
            {    
            s[0][0]=Double.parseDouble(jf1.getText().trim());   
            s[0][1]=Double.parseDouble(jf3.getText().trim());   
            s[0][2]=Double.parseDouble(jf5.getText().trim());   
            s[0][3]=Double.parseDouble(jf7.getText().trim());   
            s[0][4]=Double.parseDouble(jf9.getText().trim());   
            s[1][0]=Double.parseDouble(jf2.getText().trim());   
            s[1][1]=Double.parseDouble(jf4.getText().trim());   
            s[1][2]=Double.parseDouble(jf6.getText().trim());   
            s[1][3]=Double.parseDouble(jf8.getText().trim());   
            s[1][4]=Double.parseDouble(jf10.getText().trim());   
            ShapeMaker1 shapeMaker = new PolygonMaker1();   
            panel.setShapeMaker(shapeMaker, pointCount);   
               
            }   
         });   
     // button2.addActionListener(new ActionListener)   
     add("North",new JPanelBox(panel2,"control points (x,y)"));   
     add(panel3, BorderLayout.SOUTH);   
   
   }   
   
   private static int pointCount = 6;
   private static final int DEFAULT_WIDTH = 700;   
   private static final int DEFAULT_HEIGHT = 700;   
   static final double[][] s=new double[2][pointCount];   
}   
   
class ShapePanel1 extends JPanel   
{     
   public ShapePanel1()   
   {     
      addMouseListener(new   
         MouseAdapter()   
         {   
            public void mousePressed(MouseEvent event)   
            {     
               Point p = event.getPoint();   
               for (int i = 0; i < points.length; i++)   
               {     
                  double x = points[i].getX() - SIZE / 2;   
                  double y = points[i].getY() - SIZE / 2;   
                  Rectangle2D r = new Rectangle2D.Double(x, y, SIZE, SIZE);   
                  if (r.contains(p))   
                  {     
                     current = i;   
                     return;   
                  }   
               }   
            }   
   
            public void mouseReleased(MouseEvent event)   
            {     
               current = -1;   
            }   
         });   
      addMouseMotionListener(new    
         MouseMotionAdapter()   
         {   
            public void mouseDragged(MouseEvent event)   
            {     
               if (current == -1) return;   
               points[current] = event.getPoint();   
               repaint();   
               double[][] tf= new double[2][pointCount];   
               DecimalFormat df = new DecimalFormat("###.00");   
               for(int j=0;j<5;j++)   
                {   
                    tf[0][j]=50*ShapePanel1.points[j].getX()/getWidth()-35;   
                    tf[1][j]=50*(getHeight()-ShapePanel1.points[j].getY())/getHeight()-35;   
                }   
               BsplineCurveFrame.jf1.setText(df.format(tf[0][0]));   
               BsplineCurveFrame.jf2.setText(df.format(tf[1][0]));   
               BsplineCurveFrame.jf3.setText(df.format(tf[0][1]));   
               BsplineCurveFrame.jf4.setText(df.format(tf[1][1]));   
               BsplineCurveFrame.jf5.setText(df.format(tf[0][2]));   
               BsplineCurveFrame.jf6.setText(df.format(tf[1][2]));   
               BsplineCurveFrame.jf7.setText(df.format(tf[0][3]));   
               BsplineCurveFrame.jf8.setText(df.format(tf[1][3]));   
               BsplineCurveFrame.jf9.setText(df.format(tf[0][4]));   
               BsplineCurveFrame.jf10.setText(df.format(tf[1][4]));   
            }   
         });   
      current = -1;   
   }   
        
   public void setShapeMaker(ShapeMaker1 aShapeMaker, int n)   
   {     
      shapeMaker = aShapeMaker;   
//      int n = shapeMaker.getPointCount(); 
      this.setPointCount(n);
      points = new Point2D[n];     
        double[][] a=BsplineCurveFrame.s;   
        for(int i=0;i<n;i++)   
        {      
            double x = getWidth()/50*(a[0][i]+35);   
            double y = getHeight()-getHeight()/50*(a[1][i]+35);   
            points[i] = new Point2D.Double(x, y);   
         }   
        
      repaint();   
   }    
   public void paintComponent(Graphics g)   
   {     
      super.paintComponent(g);   
         
      if (points == null) return;   
      Graphics2D g2 = (Graphics2D) g;   
      g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING,RenderingHints.VALUE_ANTIALIAS_ON);   
      BasicStroke bs= new BasicStroke(1.0f,BasicStroke.CAP_SQUARE,   
          BasicStroke.JOIN_MITER);   
      g2.setStroke(bs);   
      g2.setColor(Color.green); 
      for (int j = 0; j < points.length; j++)   // puts a square at each control point location
      {  double x = points[j].getX() - SIZE / 2;   
         double y = points[j].getY() - SIZE / 2;     
         g2.fill(new Rectangle2D.Double(x, y, SIZE, SIZE));   
      }   
   
      g2.setColor(Color.red); 
      g2.draw(shapeMaker.makeShape(points));   // draws the lines

      double[] x1=new double[1001];   
      double[] y1=new double[1001];   
      double[] w1=new double[2];   
      
      int n = 5;
      int k = 3;
      
      for(int i=0;i<1000;i++)   				// is 1000 then the resolution of the B-splines?
      {      
    	  double[][] d=new double[2][getPointCount()];   
    	  for(int j=0;j<points.length;j++)   	// this just builds a matrix copy of 'points'
    	  {   
    		  d[0][j]=points[j].getX();   
    		  d[1][j]=points[j].getY();   
    	  }   
    	  double u=0.001*i+0.001;   			// in for loop u goes from 0.001 to 1
    	  double[] u1=H.Hartleyknot(d,n,k);     // computes knot vector?
    	  double[] t=H.HartleyT(u1,n,k);   		// pulls middle 3 members of u1 array: [0 0.48 1]
    	  int[] r={4,1,4};   					// 
    	  w1=BNote(t,r,u,d);   					// BNote([0 0.48 1],[4 1 4],{0.001 to 1},control points matrix)
    	  x1[i]=w1[0];   
    	  y1[i]=w1[1];   
      }   
      
	  g2.setColor(Color.blue);   
      for(int i=0;i<=998;i++)   
      {   
    	  line2=new Line2D.Double(x1[i],y1[i],x1[i+1],y1[i+1]);   
    	  g2.draw(line2);   

      }   
      System.out.println("oop");
   
    }   
       
    public   double[]  BNote(double[] t,int[] r,double u,double[][] d)   
    {       
        double x[]=new double[2];   
        double[][] c=d;   
        int i=0,k=3;   
        for(int j=0;j<8;j++)   											// from 0 to 7: 
        {   
            if(u<=knotValue(j+1,t,r)&&u>knotValue(j,t,r))   
            {   
                i=j;   
                break;   
            }   
        }   
           
        for(int q=1;q<=k;q++)   
        {   
            for(int j=i-k;j<=i-q;j++)   
            {   
                double alfa=knotValue(j+k+1,t,r)-knotValue(j+q,t,r);   
                if(alfa==0)alfa=0;   
                else   
                alfa=(u-knotValue(j+q,t,r))/alfa;   
                c[0][j]=(1-alfa)*c[0][j]+alfa*c[0][j+1];   
                c[1][j]=(1-alfa)*c[1][j]+alfa*c[1][j+1];   
            }   
        }   
        for(int m=0;m<2;m++)   
        {   
            x[m]=c[m][i-k];   
        }    
            
        return x;    
    }   
    public double knotValue(int k,double t[],int r[])   
    {   
        int j=1;   
        double temp=0;   
        for(int i=0;i<r.length;i++)   
        {   
            temp=temp+r[i];   
            if(temp>k)   
            {   
                j=i;   
                break;   
            }   
        }   
        return t[j];   
           
    }   
   
    public int getPointCount() {
    	return pointCount;
    }

    public void setPointCount(int pointCount) {
    	ShapePanel1.pointCount = pointCount;
    }
   
   private static int pointCount;
   public  static Point2D[] points;   
   private static int SIZE = 10;   
   private int current;   
   private ShapeMaker1 shapeMaker;   
   private Line2D line2;   
   private HartleyJ H=new HartleyJ();   
}   
abstract class ShapeMaker1   
{     
   
   public ShapeMaker1(int aPointCount)   
   {     
      pointCount = aPointCount;   
   }   
   
   public int getPointCount()   
   {     
      return pointCount;   
   }   
   public abstract Shape makeShape(Point2D[] p);   
   
   public String toString()   
   {     
      return getClass().getName();   
   }   
   
   private int pointCount;   
}   
class PolygonMaker1 extends ShapeMaker1   
{     
   public PolygonMaker1() { super(5); }   
   
   public Shape makeShape(Point2D[] p)   
   {     
      GeneralPath s = new GeneralPath();   
      s.moveTo((float) p[0].getX(), (float) p[0].getY());   
      for (int i = 1; i < p.length; i++)   
         s.lineTo((float) p[i].getX(), (float) p[i].getY());   
      return s;   
   }   
}   
   
class MyWindowListener extends WindowAdapter   
{   
    public void windowClosing(WindowEvent e)   
    {   
    System.exit(0);   
    }   
}  
