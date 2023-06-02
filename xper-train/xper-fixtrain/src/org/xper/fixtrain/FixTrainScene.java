package org.xper.fixtrain;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.Drawable;
import org.xper.experiment.ExperimentTask;
import org.xper.experiment.listener.ExperimentEventListener;
import org.xper.eye.EyeMonitor;
import org.xper.eye.listener.EyeDeviceMessageListener;
import org.xper.fixcal.FixCalEventListener;
import org.xper.fixtrain.drawing.FixTrainBlankObject;
import org.xper.fixtrain.drawing.FixTrainDrawable;
import org.xper.fixtrain.drawing.FixTrainFixationPoint;
import org.xper.util.EventUtil;

import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;

public class FixTrainScene extends AbstractTaskScene implements TrialEventListener,
        EyeDeviceMessageListener,
        ExperimentEventListener {

    @Dependency
    Map<String, FixTrainDrawable<?>> fixTrainObjectMap;

    @Dependency
    double calibrationDegree;

    @Dependency
    List<FixCalEventListener> fixCalEventListeners;

    @Dependency
    EyeMonitor eyeMonitor;

    private FixTrainStimSpec spec;

    private Coordinates2D[] calibrationPoints = new Coordinates2D[] {
            new Coordinates2D(0, 0), new Coordinates2D(1, 0),
            new Coordinates2D(-1, 0), new Coordinates2D(0, 1),
            new Coordinates2D(0, -1) };
    private int currentPointIndex = 0;
    private final AtomicBoolean trialSucceed = new AtomicBoolean(false);

    @Override
    public Drawable getFixation() {
        return new Drawable() {
            @Override
            public void draw(Context context) {
                drawFixation(context);
            }
        };
    }

    private void drawFixation(Context context) {
        FixTrainDrawable<?> obj = currentFixationPoint();
        if (obj != null) {
            GL11.glStencilFunc(GL11.GL_EQUAL, 0, 0);
            obj.draw(context);

        }
    }

    private FixTrainDrawable<?> currentFixationPoint() {
        String objClass;
        if (spec != null) {
            objClass = spec.getStimClass();
        } else {
            objClass = FixTrainFixationPoint.class.getName();
        }
        return fixTrainObjectMap.get(objClass);
    }

    @Override
    public void setTask(ExperimentTask task) {

    }


    @Override
    public void trialStart(long timestamp, TrialContext context) {
        trialSucceed.set(false);
        fireCalibrationPointSetupEvent(timestamp, context);

        ExperimentTask task = context.getCurrentTask();
        spec = FixTrainStimSpec.fromXml(task.getStimSpec());
        if (spec != null) {
            FixTrainDrawable<?> obj = currentFixationPoint();
            if (obj != null) {
                obj.setSpec(spec.getStimSpec());
            }
        } else{
            String objClass = FixTrainFixationPoint.class.getName();
            FixTrainDrawable<?> obj = fixTrainObjectMap.get(objClass);
            obj.setSpec(spec.getStimSpec());
        }
    }

    private void fireCalibrationPointSetupEvent(long timestamp, TrialContext context) {
        double x = calibrationPoints[currentPointIndex].getX()
                * calibrationDegree;
        double y = calibrationPoints[currentPointIndex].getY()
                * calibrationDegree;
        EventUtil.fireCalibrationPointSetupEvent(timestamp,
                fixCalEventListeners, new Coordinates2D(x, y), context);
    }

    @Override
    public void trialStop(long timestamp, TrialContext context) {
        if (trialSucceed.get()) {
            setupCalibrationPoint();
        }
    }

    @Override
    public void experimentStart(long timestamp) {
        setupCalibrationPoint();
    }

    private void setupCalibrationPoint() {
        double x = calibrationPoints[currentPointIndex].getX()
                * calibrationDegree;
        double y = calibrationPoints[currentPointIndex].getY()
                * calibrationDegree;
        Coordinates2D calibrationPointPositionDegrees = new Coordinates2D(x, y);
        currentFixationPoint().next(calibrationPointPositionDegrees);
        eyeMonitor.setEyeWinCenter(calibrationPointPositionDegrees);
    }

    @Override
    public void trialComplete(long timestamp, TrialContext context) {
        currentPointIndex = (currentPointIndex + 1) % calibrationPoints.length;
        trialSucceed.set(true);
    }



    @Override
    public void trialInit(long timestamp, TrialContext context) {

    }

    @Override
    public void drawStimulus(Context context) {

    }

    @Override
    public void fixationPointOn(long timestamp, TrialContext context) {

    }

    @Override
    public void initialEyeInFail(long timestamp, TrialContext context) {

    }

    @Override
    public void initialEyeInSucceed(long timestamp, TrialContext context) {

    }

    @Override
    public void eyeInHoldFail(long timestamp, TrialContext context) {

    }

    @Override
    public void fixationSucceed(long timestamp, TrialContext context) {

    }

    @Override
    public void eyeInBreak(long timestamp, TrialContext context) {

    }

    @Override
    public void experimentStop(long timestamp) {

    }

    @Override
    public void eyeDeviceMessage(long timestamp, String id, Coordinates2D volt, Coordinates2D degree) {

    }


    private void setDefaultSpec(FixTrainDrawable drawable){
        drawable.setSpec("");
    }

    public Map<String, FixTrainDrawable<?>> getFixTrainObjectMap() {
        return fixTrainObjectMap;
    }

    public void setFixTrainObjectMap(Map<String, FixTrainDrawable<?>> fixTrainObjectMap) {
        this.fixTrainObjectMap = fixTrainObjectMap;
    }

    public double getCalibrationDegree() {
        return calibrationDegree;
    }

    public void setCalibrationDegree(double calibrationDegree) {
        this.calibrationDegree = calibrationDegree;
    }

    public List<FixCalEventListener> getFixCalEventListeners() {
        return fixCalEventListeners;
    }

    public void setFixCalEventListeners(List<FixCalEventListener> fixCalEventListeners) {
        this.fixCalEventListeners = fixCalEventListeners;
    }

    public EyeMonitor getEyeMonitor() {
        return eyeMonitor;
    }

    public void setEyeMonitor(EyeMonitor eyeMonitor) {
        this.eyeMonitor = eyeMonitor;
    }
}