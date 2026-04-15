package org.xper.rfplot;

import java.util.Map;
import java.util.Objects;
import java.util.Timer;
import java.util.TimerTask;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.drawing.Drawable;
import org.xper.experiment.ExperimentTask;
import org.xper.rfplot.drawing.RFPlotBlankObject;
import org.xper.rfplot.drawing.RFPlotDrawable;

public class RFPlotScene extends AbstractTaskScene {
    @Dependency
    Map<String, RFPlotDrawable> rfObjectMap;

    RFPlotStimSpec spec;
    RFPlotXfmSpec xfm;

    private Timer timer;
    private boolean isOnInterval = true; // Initial state
    private long onDuration = 500; // On interval duration
    private long offDuration = 500; // Off interval duration


    @Override
    public void trialStart(TrialContext context) {
        startTimer();
        marker.next();

    }

    @Override
    public void trialStop(TrialContext context) {
        stopTimer();
    }
    public void startTimer() {
        if (timer != null) {
            timer.cancel();
        }
        timer = new Timer();

        // Start the sequence by scheduling the "turn on" task immediately
        scheduleOnTask();
    }

    private void scheduleOnTask() {
        TimerTask onTask = new TimerTask() {
            @Override
            public void run() {
                isOnInterval = true;
                scheduleOffTask();
            }
        };
        if (timer != null) {
            timer.schedule(onTask, onDuration);
        }
    }

    private void scheduleOffTask() {
        TimerTask offTask = new TimerTask() {
            @Override
            public void run() {
                isOnInterval = false;
                scheduleOnTask();
            }
        };
        if (timer != null) {
            timer.schedule(offTask, offDuration);
        }
    }


    public void stopTimer() {
        if (timer != null) {
            timer.cancel();
            timer = null;
        }
    }
    public void initGL(int w, int h) {
        super.initGL(w, h);
        // TODO: initGL for objects


    }

    public void setTask(ExperimentTask task) {
        spec = RFPlotStimSpec.fromXml(task.getStimSpec());
        if (spec != null) {
            String objClass = spec.getStimClass();
            RFPlotDrawable obj = rfObjectMap.get(objClass);
            if (obj != null) {
                obj.setSpec(spec.getStimSpec());
            }
        } else{
            String objClass = RFPlotBlankObject.class.getName();
            RFPlotDrawable obj = rfObjectMap.get(objClass);
            obj.setDefaultSpec();
        }
        xfm = RFPlotXfmSpec.fromXml(task.getXfmSpec());
    }

    @Override
    public void drawTask(Context context, boolean fixationOn) {
        // clear the whole screen before define view ports in renderer
        blankScreen.draw(null);
        renderer.draw(new Drawable() {
            public void draw(Context context) {
                if (useStencil) {
                    if (fixationOn) {
                        // Normal behavior - stimulus only in region 0
                        GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
                    } else {
                        // Allow stimulus in both regions 0 and 1
                        GL11.glStencilFunc(GL11.GL_NOTEQUAL, 2, 3); // or disable stencil entirely
                    }
                }
                drawStimulus(context);
                if (useStencil) {
                    // 1 will pass for fixation and marker regions
                    GL11.glStencilFunc(GL11.GL_EQUAL, 1, 1);
                }

                if (fixationOn) {
                    getFixation().draw(context);
                }
//                marker.draw(context);
                if (Objects.equals(spec.getStimClass(), "org.xper.rfplot.drawing.RFPlotBlankObject")) {
                    System.out.println("Drawing stimulus with type:" + spec.getStimClass());
                    marker.drawAllOff(context);
                } else{
                    marker.draw(context);
                }
                if (useStencil) {
                    // 0 will pass for stimulus region
                    GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
                }
            }}, context);
    }

    public void drawStimulus(Context context) {
//		if (isOnInterval) {

        if (true) {
            if (spec == null) return;



            //if blank here, we don't draw, if it is anything else, we draw
            GL11.glShadeModel(GL11.GL_SMOOTH);
            GL11.glDisable(GL11.GL_DEPTH_TEST);

            String objClass = spec.getStimClass();
            RFPlotDrawable obj = rfObjectMap.get(objClass);
            if (obj != null) {
                GL11.glPushAttrib(GL11.GL_ALL_ATTRIB_BITS);
                GL11.glPushMatrix();
                // Enable blending
                GL11.glEnable(GL11.GL_BLEND);
                // Set blending function to approximate color multiplication
                GL11.glColor3f(xfm.getColor().getRed(), xfm.getColor().getGreen(), xfm.getColor().getBlue());

                GL11.glTranslated(xfm.getTranslation().getX(), xfm.getTranslation().getY(), 1.0);
                GL11.glRotatef(xfm.getRotation(), 0.0f, 0.0f, 1.0f);
                GL11.glScaled(xfm.getScale().getX(), xfm.getScale().getY(), 1.0);

                GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT | GL11.GL_STENCIL_BUFFER_BIT);
                obj.draw(context);

                GL11.glPopMatrix();
                GL11.glPopAttrib();
            }
        } else{
            drawBlank(context, true, false);
        }
    }

    public Map<String, RFPlotDrawable> getRfObjectMap() {
        return rfObjectMap;
    }

    public void setRfObjectMap(Map<String, RFPlotDrawable> rfObjectMap) {
        this.rfObjectMap = rfObjectMap;
    }

}