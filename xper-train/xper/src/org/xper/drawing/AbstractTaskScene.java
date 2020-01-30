package org.xper.drawing;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.renderer.Renderer;

public abstract class AbstractTaskScene implements TaskScene {
	
	@Dependency
	protected Renderer renderer;
	@Dependency
	protected Drawable fixation;
	@Dependency
	protected Drawable blankScreen;
	@Dependency
	protected ScreenMarker marker;
	@Dependency
	protected boolean useStencil = true;

	public void initGL(int w, int h) {
		renderer.init(w, h);
		if (useStencil) {
			GL11.glClear (GL11.GL_STENCIL_BUFFER_BIT);
			// disable color and depth buffer for writing
			GL11.glColorMask(false, false, false, false);
			GL11.glDepthMask(false);
			GL11.glEnable(GL11.GL_STENCIL_TEST);
			// write 1 to stencil buffer for fixation point and marker regions
			GL11.glStencilFunc(GL11.GL_NEVER, 1, 1);
			GL11.glStencilOp(GL11.GL_REPLACE, GL11.GL_KEEP, GL11.GL_KEEP);
			renderer.draw(new Drawable() {
				public void draw(Context context) {	
					fixation.draw(context);
					marker.draw(context);
				}
			}, new Context());
			// write protected stencil buffer
			GL11.glStencilOp(GL11.GL_KEEP, GL11.GL_KEEP, GL11.GL_KEEP);
			GL11.glStencilMask(0);
			// enable color and depth buffer for writing
			GL11.glColorMask(true, true, true, true);
			GL11.glDepthMask(true);
		} else {
			// GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT | GL11.GL_STENCIL_BUFFER_BIT);
		}
	}

	public void drawBlank(Context context, final boolean fixationOn, final boolean markerOn) {
		blankScreen.draw(null);
		renderer.draw(new Drawable() {
			public void draw(Context context) {		
				if (useStencil) {
					// 1 will pass for fixation and marker regions
					GL11.glStencilFunc(GL11.GL_EQUAL, 1, 1);
				}
				if (fixationOn) {
					fixation.draw(context);
				}
				if (markerOn) {
					marker.draw(context);
				} else {
					marker.drawAllOff(context);
				}
				if (useStencil) {
					// 0 will pass for stimulus region
					GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
				}
				drawCustomBlank(context);
			}}, context);
	}
	
	protected void drawCustomBlank(Context context) {}
	
	public void drawTask(Context context, final boolean fixationOn) {
		// clear the whole screen before define view ports in renderer
		blankScreen.draw(null);
		renderer.draw(new Drawable() {
			public void draw(Context context) {
				if (useStencil) {
					// 0 will pass for stimulus region
					GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
				}
				drawStimulus(context);
				if (useStencil) {
					// 1 will pass for fixation and marker regions
					GL11.glStencilFunc(GL11.GL_EQUAL, 1, 1);
				}
				
				if (fixationOn) {
					 fixation.draw(context);
				}
				marker.draw(context);
				if (useStencil) {
					// 0 will pass for stimulus region
					GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
				}
			}}, context);
	}

	public void nextMarker() {
		marker.next();
	}
	
	public void trialStart(TrialContext context) {
	}

	public void trialStop(TrialContext context) {
	}
	
	public Drawable getFixation() {
		return fixation;
	}

	public void setFixation(Drawable fixation) {
		this.fixation = fixation;
	}

	public Drawable getBlankScreen() {
		return blankScreen;
	}

	public void setBlankScreen(Drawable blankScreen) {
		this.blankScreen = blankScreen;
	}
	
	public Renderer getRenderer() {
		return renderer;
	}

	public void setRenderer(Renderer renderer) {
		this.renderer = renderer;
	}
	
	public ScreenMarker getMarker() {
		return marker;
	}

	public void setMarker(ScreenMarker marker) {
		this.marker = marker;
	}
	
	public boolean isUseStencil() {
		return useStencil;
	}

	public void setUseStencil(boolean useStencil) {
		this.useStencil = useStencil;
	}
}
