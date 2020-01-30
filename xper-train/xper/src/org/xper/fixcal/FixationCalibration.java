package org.xper.fixcal;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;

import org.apache.commons.math.stat.descriptive.DescriptiveStatistics;
import org.apache.commons.math.stat.descriptive.SummaryStatistics;
import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.object.FixationPoint;
import org.xper.experiment.ExperimentTask;
import org.xper.experiment.listener.ExperimentEventListener;
import org.xper.eye.EyeMonitor;
import org.xper.eye.listener.EyeDeviceMessageListener;
import org.xper.util.DbUtil;
import org.xper.util.EventUtil;

public class FixationCalibration extends AbstractTaskScene implements TrialEventListener,
		EyeDeviceMessageListener, ExperimentEventListener {
	static Logger logger = Logger.getLogger(FixationCalibration.class);

	@Dependency
	double calibrationDegree;
	@Dependency
	FixationPoint fixationPoint;
	@Dependency
	EyeMonitor eyeMonitor;
	@Dependency
	HashMap<String, String> deviceDbVariableMap;
	@Dependency
	HashMap<String, String> eyeZeroDbVariableMap;
	@Dependency
	List<FixCalEventListener> fixCalEventListeners;
	@Dependency
	DbUtil dbUtil;


	static int CENTER = 0;
	static int UP = 3;
	static int DOWN = 4;
	static int RIGHT = 1;
	static int LEFT = 2;

	static int H = 0;
	static int V = 1;
	static int DIM = 2;
	
	static int MIN_SAMPLE_COUNT = 10;

	Coordinates2D[] calibrationPoints = new Coordinates2D[] {
			new Coordinates2D(0, 0), new Coordinates2D(1, 0),
			new Coordinates2D(-1, 0), new Coordinates2D(0, 1),
			new Coordinates2D(0, -1) };
	int currentPointIndex = 0;

	/**
	 * device id => descriptive statistics [points][h or v]
	 */ 
	HashMap<String, DescriptiveStatistics[][]> currentTrialStat = new HashMap<String, DescriptiveStatistics[][]>();
	AtomicBoolean recordEyeReading = new AtomicBoolean(false);
	AtomicBoolean trialSucceed = new AtomicBoolean(false);
	HashMap<String, SummaryStatistics[][]> summaryStat = new HashMap<String, SummaryStatistics[][]>();
	
	public void initGL(int w, int h) {
		useStencil = false;
		super.initGL(w, h);
	}

	public void setTask(ExperimentTask task) {
	}

	public void drawStimulus(Context context) {
	}

	public void eyeInBreak(long timestamp, TrialContext context) {
		recordEyeReading.set(false);
	}

	public void eyeInHoldFail(long timestamp, TrialContext context) {
		recordEyeReading.set(false);
	}

	public void fixationPointOn(long timestamp, TrialContext context) {
	}

	public void fixationSucceed(long timestamp, TrialContext context) {
		recordEyeReading.set(true);
	}

	public void initialEyeInFail(long timestamp, TrialContext context) {
		recordEyeReading.set(false);
	}

	public void initialEyeInSucceed(long timestamp, TrialContext context) {
	}

	public void trialComplete(long timestamp, TrialContext context) {
		recordEyeReading.set(false);
		currentPointIndex = (currentPointIndex + 1) % calibrationPoints.length;
		trialSucceed.set(true);
	}

	void calcuateTrialStat() {
		for (Map.Entry<String, DescriptiveStatistics[][]> ent : currentTrialStat
				.entrySet()) {
			String id = ent.getKey();
			DescriptiveStatistics[][] stats = ent.getValue();
			SummaryStatistics[][] summary = summaryStat.get(id);
			for (int i = 0; i < stats.length; i++) {
				for (int j = 0; j < stats[i].length; j++) {
					if (stats[i][j].getN() >= MIN_SAMPLE_COUNT) {
						DescriptiveStatistics result = removeOutliers(stats[i][j]);
						double avg = result.getMean();
						summary[i][j].addValue(avg);
						if (logger.isDebugEnabled()) {
							logger.debug(i + " " + j + " " + avg);
						}
					}
				}
			}
		}
	}

	DescriptiveStatistics removeOutliers(DescriptiveStatistics stat) {
		DescriptiveStatistics result = DescriptiveStatistics.newInstance();
		double median = stat.getPercentile(50);
		double q3 = stat.getPercentile(75);
		double q1 = stat.getPercentile(25);
		double range = q3 - q1;
		double[] data = stat.getValues();
		for (int i = 0; i < data.length; i++) {
			if (range <= 0 || Math.abs(data[i] - median) < 1.5 * range) {
				result.addValue(data[i]);
			} else {
				if (logger.isDebugEnabled()) {
					logger.debug("Removing outlier " + data[i]);
				}
			}
		}
		return result;
	}
	
	public void trialInit(long timestamp, TrialContext context) {
	}

	public void trialStart(long timestamp, TrialContext context) {
		recordEyeReading.set(false);
		trialSucceed.set(false);

		for (DescriptiveStatistics[][] stat : currentTrialStat.values()) {
			for (int i = 0; i < stat.length; i++) {
				for (int j = 0; j < stat[i].length; j++) {
					stat[i][j] = DescriptiveStatistics.newInstance();
				}
			}
		}

		fireCalibrationPointSetupEvent(timestamp, context);
	}

	public void trialStop(long timestamp, TrialContext context) {
		if (trialSucceed.get()) {
			calcuateTrialStat();
			setupCalibrationPoint();
		}
	}

	void setupCalibrationPoint() {
		double x = calibrationPoints[currentPointIndex].getX()
				* calibrationDegree;
		double y = calibrationPoints[currentPointIndex].getY()
				* calibrationDegree;
		fixationPoint.setFixationPosition(new Coordinates2D(x, y));
		eyeMonitor.setEyeWinCenter(new Coordinates2D(x, y));
	}

	void fireCalibrationPointSetupEvent(long timestamp, TrialContext context) {
		double x = calibrationPoints[currentPointIndex].getX()
				* calibrationDegree;
		double y = calibrationPoints[currentPointIndex].getY()
				* calibrationDegree;
		EventUtil.fireCalibrationPointSetupEvent(timestamp,
				fixCalEventListeners, new Coordinates2D(x, y), context);
	}

	public void eyeDeviceMessage(long timestamp, String id, Coordinates2D volt,
			Coordinates2D degree) {
		if (recordEyeReading.get()) {
			DescriptiveStatistics[][] stat = currentTrialStat.get(id);
			stat[currentPointIndex][H].addValue(volt.getX());
			stat[currentPointIndex][V].addValue(volt.getY());
		}
	}

	public void experimentStart(long timestamp) {
		for (String key : deviceDbVariableMap.keySet()) {
			currentTrialStat.put(key,
					new DescriptiveStatistics[calibrationPoints.length][DIM]);
			summaryStat.put(key,
					new SummaryStatistics[calibrationPoints.length][DIM]);
		}
		for (SummaryStatistics[][] s : summaryStat.values()) {
			for (int i = 0; i < s.length; i++) {
				for (int j = 0; j < s[i].length; j++) {
					s[i][j] = SummaryStatistics.newInstance();
				}
			}
		}

		setupCalibrationPoint();
	}

	public void experimentStop(long timestamp) {
		for (Map.Entry<String, SummaryStatistics[][]> ent : summaryStat
				.entrySet()) {
			String id = ent.getKey();
			logger.info("----------------------------- " + id
					+ " --------------------------------");
			SummaryStatistics[][] stats = ent.getValue();
			
			double h0 = stats[CENTER][H].getMean();
			double v0 = stats[CENTER][V].getMean();
			System.out.println("Center estimate = " + h0 + ", " + v0);
			logger.info("h0: " + h0 + " v0: " + v0);
			
			double hr = stats[RIGHT][H].getMean();
			double vr = stats[RIGHT][V].getMean();
			System.out.println("Right estimate = " + hr + ", " + vr);
			logger.info("hr: " + hr + " vr: " + vr);
			double sxh_r = (hr - h0) / calibrationDegree;
			double sxv_r = (vr - v0) / calibrationDegree;
			
			double hl = stats[LEFT][H].getMean();
			double vl = stats[LEFT][V].getMean();
			System.out.println("Left estimate = " + hl + ", " + vl);
			logger.info("hl: " + hl + " vl: " + vl);
			double sxh_l = ( hl - h0) / (-calibrationDegree);
			double sxv_l = ( vl - v0) / (-calibrationDegree);
			
			double hu = stats[UP][H].getMean();
			double vu = stats[UP][V].getMean();
			System.out.println("Up estimate = " + hu + ", " + vu);
			logger.info("hu: " + hu + " vu: " + vu);
			double syh_u =  (hu - h0) / calibrationDegree;
			double syv_u =  (vu - v0) / calibrationDegree;
			
			double hd = stats[DOWN][H].getMean();
			double vd = stats[DOWN][V].getMean();
			System.out.println("Down estimate = " + hd + ", " + vd);
			logger.info("hd: " + hd + " vd: " + vd);
			double syh_d = ( hd - h0) / (-calibrationDegree);
			double syv_d = ( vd - v0) / (-calibrationDegree);

			double sxh = (sxh_r + sxh_l) / 2.0;
			double sxv = (sxv_r + sxv_l) / 2.0;
			double syh = (syh_u + syh_d) / 2.0;
			double syv = (syv_u + syv_d) / 2.0;

			logger.info("Sxh: " + sxh + " Sxv:" + sxv + " Syh: " + syh
					+ " Syv: " + syv);
			
			if (isValid(sxh) && isValid(sxv) && isValid(syh) && isValid(syv) && isValid(h0) && isValid(v0)) {
				String varName = deviceDbVariableMap.get(id);
				dbUtil.writeSystemVar(varName, 0, String.valueOf(sxh), timestamp);
				dbUtil.writeSystemVar(varName, 1, String.valueOf(sxv), timestamp);
				dbUtil.writeSystemVar(varName, 2, String.valueOf(syh), timestamp);
				dbUtil.writeSystemVar(varName, 3, String.valueOf(syv), timestamp);
				
				String eyeZeroName = eyeZeroDbVariableMap.get(id);
				dbUtil.writeSystemVar(eyeZeroName, 0, String.valueOf(h0), timestamp);
				dbUtil.writeSystemVar(eyeZeroName, 1, String.valueOf(v0), timestamp);
			}
		}
	}
	
	boolean isValid(double v) {
		return !(Double.isInfinite(v) || Double.isNaN(v));
	}

	public double getCalibrationDegree() {
		return calibrationDegree;
	}

	public void setCalibrationDegree(double calibrationDegree) {
		this.calibrationDegree = calibrationDegree;
	}

	public FixationPoint getFixationPoint() {
		return fixationPoint;
	}

	public void setFixationPoint(FixationPoint fixationPoint) {
		this.fixationPoint = fixationPoint;
	}

	public EyeMonitor getEyeMonitor() {
		return eyeMonitor;
	}

	public void setEyeMonitor(EyeMonitor eyeMonitor) {
		this.eyeMonitor = eyeMonitor;
	}

	public HashMap<String, String> getDeviceDbVariableMap() {
		return deviceDbVariableMap;
	}

	public void setDeviceDbVariableMap(
			HashMap<String, String> deviceDbVariableMap) {
		this.deviceDbVariableMap = deviceDbVariableMap;
	}

	public List<FixCalEventListener> getFixCalEventListeners() {
		return fixCalEventListeners;
	}

	public void setFixCalEventListeners(
			List<FixCalEventListener> fixCalEventListeners) {
		this.fixCalEventListeners = fixCalEventListeners;
	}

	public DbUtil getDbUtil() {
		return dbUtil;
	}

	public void setDbUtil(DbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}

	public HashMap<String, String> getEyeZeroDbVariableMap() {
		return eyeZeroDbVariableMap;
	}

	public void setEyeZeroDbVariableMap(HashMap<String, String> eyeZeroDbVariableMap) {
		this.eyeZeroDbVariableMap = eyeZeroDbVariableMap;
	}

}
