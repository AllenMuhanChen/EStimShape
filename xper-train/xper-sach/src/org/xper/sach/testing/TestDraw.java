package org.xper.sach.testing;


//import java.util.ArrayList;
//import java.util.List;

import org.xper.drawing.Context;
import org.xper.drawing.Drawable;
import org.xper.sach.drawing.StimTestWindow;
//import org.xper.sach.expt.behavior.splines.MyPoint;

import org.lwjgl.opengl.GL11;
import org.lwjgl.util.glu.GLU;
import org.lwjgl.util.glu.GLUtessellator;
//import org.lwjgl.util.glu.GLUtessellatorCallback;
import org.lwjgl.util.glu.GLUtessellatorCallbackAdapter;
import org.lwjgl.util.glu.tessellation.GLUtessellatorImpl;



public class TestDraw implements Drawable {

	/**
	 * @param args
	 */
	
	//GLUtessellator m_tess;
	
	
	
	public static void main(String[] args) {

		StimTestWindow testWindow = new StimTestWindow();

		//BsplineObject s = new BsplineObject();
		//s.creatObj(0);	// create multi-limb object
		
		//BsplineObject s = new BsplineObject();
		
		TestDraw s = new TestDraw();
		
		testWindow.setStimObjs(s);		// add object to be drawn
		testWindow.testDraw();			// draw object


	}

		
	@Override
	public void draw(Context context) {
		
		double r = 10;
		double[][] vertex = {{0,0,0},{r,0,0},{r,r,0},{2*r,r,0},{2*r,-r,0},{-2*r,-r,0},{-2*r,r,0},{-r,r,0},{-r,0,0},{0,0,0}};
		boolean solid = true;
		
		
		if (solid) {

//			//int priority = 0;
//			int priority = GL11.glGenLists(10); 
//
//			GLUtessellator tesselator = GLUtessellatorImpl.gluNewTess();// = new GLUtessellatorImpl(); // = GLU.gluNewTess();
//			
//			//tesselator.gluTessNormal(0, 0, 1);
//			tesselator.gluTessCallback(GLU.GLU_TESS_BEGIN, tesscallback);
//			tesselator.gluTessCallback(GLU.GLU_TESS_VERTEX, tesscallback);
//			tesselator.gluTessCallback(GLU.GLU_TESS_COMBINE, tesscallback);
//			tesselator.gluTessCallback(GLU.GLU_TESS_END, tesscallback);
//			tesselator.gluTessCallback(GLU.GLU_TESS_ERROR, tesscallback);
//			//tesselator.gluTessCallback(GLU.GLU_TESS_BEGIN_DATA,tesscallback );
//			//tesselator.gluTessCallback(GLU.GLU_TESS_COMBINE_DATA,tesscallback );
//			GL11.glDeleteLists(priority, 1);
//			GL11.glNewList(priority, GL11.GL_COMPILE);
//			GL11.glPolygonOffset(1.0f, 1.0f);
//			GL11.glEnable(GL11.GL_POLYGON_OFFSET_FILL);
//			GL11.glColor3f(1f,0f,0f);
//			GL11.glDisable(GL11.GL_POLYGON_SMOOTH);
//			GL11.glPolygonMode(GL11.GL_FRONT_AND_BACK, GL11.GL_FILL );
//			GL11.glEnable(GL11.GL_LINE_SMOOTH);
//			GL11.glTranslatef(0.0f, 0.0f,0.01f);
//			tesselator.gluTessProperty(GLU.GLU_TESS_WINDING_RULE, GLU.GLU_TESS_WINDING_NONZERO);
//			//tesselator.gluBeginPolygon();
//			tesselator.gluTessBeginPolygon(null);
//
//			//		double[][][] vertex = { {{0,0},{1,1},{1,-1},{-1,-1},{-1,1},{0,0}},{{5,0},{6,1},{6,-1},{-4,-1},{-4,1},{5,0}} };
//
//			tesselator.gluTessBeginContour();
//			for(double[] vertex_list:vertex){
//				tesselator.gluTessVertex(vertex_list, 0, vertex_list);
//				//tesselator.gluTessVertex(vertex_list, 0, new VertexData(vertex_list));
//			}
//			tesselator.gluTessEndContour();
//
//			//tesselator.gluEndPolygon();
//			tesselator.gluTessEndPolygon();

			
			// create tessellator
			GLUtessellator tess = GLUtessellatorImpl.gluNewTess();// = new GLUtessellatorImpl(); // = GLU.gluNewTess();
			
			// register callback functions
			tess.gluTessCallback(GLU.GLU_TESS_BEGIN, tesscallback);
			tess.gluTessCallback(GLU.GLU_TESS_END, tesscallback);
			tess.gluTessCallback(GLU.GLU_TESS_VERTEX, tesscallback);
			tess.gluTessCallback(GLU.GLU_TESS_COMBINE, tesscallback);
			tess.gluTessCallback(GLU.GLU_TESS_ERROR, tesscallback);

			
//			GL11.glDeleteLists(priority, 1);
//			GL11.glNewList(priority, GL11.GL_COMPILE);
//			GL11.glPolygonOffset(1.0f, 1.0f);
//			GL11.glEnable(GL11.GL_POLYGON_OFFSET_FILL);
			GL11.glColor3f(1f,0f,0f);
//			GL11.glDisable(GL11.GL_POLYGON_SMOOTH);
//			GL11.glPolygonMode(GL11.GL_FRONT_AND_BACK, GL11.GL_FILL );
//			GL11.glEnable(GL11.GL_LINE_SMOOTH);
//			GL11.glTranslatef(0.0f, 0.0f,0.01f);
//			tesselator.gluTessProperty(GLU.GLU_TESS_WINDING_RULE, GLU.GLU_TESS_WINDING_NONZERO);
//			//tesselator.gluBeginPolygon();

			//describe non-convex ploygon
			tess.gluTessBeginPolygon(null);
				// first contour
				tess.gluTessBeginContour();
					for (double[] v:vertex) {
						tess.gluTessVertex(v, 0, v);
						//tess.gluTessVertex(v, 0, new VertexData(v));
					}
				tess.gluTessEndContour();

				// second contour ...
				
			tess.gluTessEndPolygon();
			
			// delete tessellator after processing
			tess.gluDeleteTess();
			
			
		} else {
			// regular line drawing
			GL11.glEnable(GL11.GL_LINE_SMOOTH);
			GL11.glHint(GL11.GL_LINE_SMOOTH_HINT, GL11.GL_NICEST);
			GL11.glEnable(GL11.GL_POINT_SMOOTH);
			GL11.glHint(GL11.GL_POINT_SMOOTH_HINT, GL11.GL_NICEST);
			GL11.glEnable(GL11.GL_BLEND);
			GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
			GL11.glLineWidth(2.3f);
			GL11.glColor3f(1f,0f,0f);

			for (int i=0; i< vertex.length-1; i++) {
				drawLine(vertex[i],vertex[i+1]);
			}
			
			
//			// for solid:
//			GL11.glBegin(GL11.GL_POLYGON); //GL_QUADS); //GL_POLYGON);	
//			GL11.glColor3f(1f,0f,0f);
//			for (int i=0; i< vertex.length; i++) {
//				GL11.glVertex2d(vertex[i][0], vertex[i][1]);
//			}
//		    GL11.glEnd();
//		    GL11.glFlush();
			
		}

	}
	
	void drawLine(double[] vertex, double[] vertex2) {
	    GL11.glBegin(GL11.GL_LINES);
	    	GL11.glVertex2d(vertex[0], vertex[1]);
	    	GL11.glVertex2d(vertex2[0], vertex2[1]);
	    GL11.glEnd();
	    GL11.glFlush();
	}
	
	GLUtessellatorCallbackAdapter tesscallback = new GLUtessellatorCallbackAdapter(){
		@Override
		public void begin(int type) {
			GL11.glBegin(type);
		}

		@Override
		public void vertex(Object vertexData) {
			double[] vert = (double[]) vertexData;
			//GL11.glVertex3d(vert[0], vert[1],vert[2]);
			GL11.glVertex2d(vert[0],vert[1]);
		}

		public void combine(double[] coords, Object[] data, float[] weight, Object[] outData) {
			for (int i = 0; i < outData.length; i++) {
				double[] combined = new double[20];
				combined[0] = (double) coords[0];
				combined[1] = (double) coords[1];
				//combined[2] = (double) coords[2];
				outData[i] = combined;
			}
		}

		@Override
		public void end() {
			GL11.glEnd();
		}

		public void error(int errnum) {
			String estring;
			estring = GLU.gluErrorString(errnum);
			System.err.println("Tessellation Error Number: " + errnum);
			System.err.println("Tessellation Error: " + estring);
		}
	};
	
	
	class VertexData {
		public double[] data;

		VertexData(double[] data) {
			this.data = data;
		}
	}
	
}



