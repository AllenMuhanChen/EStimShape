package org.xper.drawing;

import java.util.ArrayList;
import java.util.List;

import org.lwjgl.opengl.GL11;
import org.xper.ManualTest;
import org.xper.XperConfig;
import org.xper.console.CommandListener;
import org.xper.console.ConsoleWindow;
import org.xper.drawing.object.Square;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveRenderer;
import org.xper.time.DefaultTimeUtil;
import org.xper.time.TimeUtil;
import org.xper.util.ThreadUtil;

@ManualTest
public class FpsTest implements CommandListener, Drawable {
	boolean done = false;
	float angle = 0;
	
	public static void main(String[] args) {
		new FpsTest().testDraw();
	}
	
	public void testDraw() {
		List<String> libs = new ArrayList<String>();
		libs.add("xper");
		new XperConfig("", libs);
		
		ConsoleWindow window = new ConsoleWindow();
		ArrayList<CommandListener> commandListeners = new ArrayList<CommandListener>();
		commandListeners.add(this);
		window.setCommandListeners(commandListeners);
		window.create();
		
		AbstractRenderer renderer = new PerspectiveRenderer();
		renderer.setDepth(3000);
		renderer.setDistance(500);
		renderer.setPupilDistance(50);
		renderer.setHeight(200);
		renderer.setWidth(300);
		renderer.init(window.getWidth(), window.getHeight());
		Context context = new Context();
		
		GL11.glShadeModel(GL11.GL_SMOOTH);
		GL11.glDisable(GL11.GL_DEPTH_TEST);
		
		TimeUtil t = new DefaultTimeUtil();
		
		int i = 0;
		long startTime = t.currentTimeMicros();
		while(!done) {
			GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT
					| GL11.GL_STENCIL_BUFFER_BIT);
			renderer.draw(this, context);
			window.swapBuffers();
			i ++;
			if (i % 1000 == 0) {
				long stopTime = t.currentTimeMicros();
				double fps = i * 1000000 / (stopTime - startTime);
				System.out.println(fps + " fps");
				ThreadUtil.sleep(2000);
				i = 0;
				startTime = t.currentTimeMicros();
			}
		}
		window.destroy();
	}
	
	public void draw(Context context) {
		GL11.glColor3d(1.0, 0.0, 1.0);
		GL11.glPushMatrix();
		GL11.glRotatef(angle, 0, 0, 1);
		Square s = new Square();
		s.setSize(50);
		s.draw(null);
		GL11.glPopMatrix();
		angle += 10;
	}

	public void experimentPause() {
	}

	public void experimentResume() {
	}

	public void experimentStop() {
		done = true;
	}
}
