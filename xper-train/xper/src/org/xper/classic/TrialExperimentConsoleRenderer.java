package org.xper.classic;

import java.util.Map;

import org.xper.Dependency;
import org.xper.classic.vo.TrialContext;
import org.xper.console.ConsoleRenderer;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.Drawable;
import org.xper.drawing.GLUtil;
import org.xper.drawing.object.Circle;
import org.xper.drawing.object.Square;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.eye.vo.EyeDeviceReading;
import org.xper.eye.vo.EyeWindow;

public class TrialExperimentConsoleRenderer implements ConsoleRenderer {
	@Dependency
	private AbstractRenderer renderer;
	@Dependency
	private
	Drawable fixation;
	@Dependency
	private
	Drawable blankScreen;
	@Dependency
	private
	Circle circle;
	@Dependency
	private
	Square square;

	private double eyeIndicatorSize = 2.5;
	private double voltageIndicatorSize = 5;
	private double voltageMin = -10.0;
	private double voltageMax = 10.0;

	@Dependency
	private
	TrialExperimentMessageHandler messageHandler;

	@Override
	public void drawCanvas(Context context, String devId) {
		getBlankScreen().draw(null);
		if (getMessageHandler().isFixationOn()) {
			drawFixation();
			drawEyeWindow();
		}
		drawEyeDeviceReading(devId);
	}

	protected void drawEyeDevice(String devId) {
		drawEyeWindow();
		drawEyeDeviceReading(devId);
	}

	protected void drawEyeWindow() {
		EyeWindow window = getMessageHandler().getEyeWindow();
		Coordinates2D eyeWindowCenter = window.getCenter();
		double eyeWindowCenterX = getRenderer().deg2mm(eyeWindowCenter.getX());
		double eyeWindowCenterY = getRenderer().deg2mm(eyeWindowCenter.getY());
		double eyeWindowSize = getRenderer().deg2mm(window.getSize());

		GLUtil.drawCircle(getCircle(), eyeWindowSize, false, eyeWindowCenterX, eyeWindowCenterY, 0.0);
	}

	protected void drawEyeDeviceReading(String devId) {
		for (Map.Entry<String, EyeDeviceReading> ent : getMessageHandler()
				.getEyeDeviceReadingEntries()) {

			String id = ent.getKey();
			if (!id.equalsIgnoreCase(devId)) {
				continue;
			}

			EyeDeviceReading reading = ent.getValue();

			// Eye Position
			Coordinates2D eyeDegree = reading.getDegree();

			boolean solid = false;
			if (getMessageHandler().isEyeIn()) {
				solid = true;
			}
			GLUtil.drawCircle(getCircle(), getEyeIndicatorSize(), solid, getRenderer().deg2mm(eyeDegree.getX()), getRenderer()
					.deg2mm(eyeDegree.getY()), 0.0);

			// Eye Voltage
			Coordinates2D eyeVolt = reading.getVolt();
			double xmin = getRenderer().getXmin();
			double xmax = getRenderer().getXmax();

			double ymin = getRenderer().getYmin();
			double ymax = getRenderer().getYmax();

			float xmm = (float) ((eyeVolt.getX() - getVoltageMin()) * (xmax - xmin)
					/ (getVoltageMax() - getVoltageMin()) + xmin);
			float ymm = (float) ((eyeVolt.getY() - getVoltageMin()) * (ymax - ymin)
					/ (getVoltageMax() - getVoltageMin()) + ymin);

			GLUtil.drawSquare(getSquare(), getVoltageIndicatorSize(), true, xmm, ymm, 0);
		}
	}

	protected void drawFixation() {
		if (getMessageHandler().isFixationOn()) {
			TrialContext context = new TrialContext();
			context.setRenderer(getRenderer());
			getFixation().draw(context);
		}
	}

	public TrialExperimentMessageHandler getMessageHandler() {
		return messageHandler;
	}

	public void setMessageHandler(TrialExperimentMessageHandler messageHandler) {
		this.messageHandler = messageHandler;
	}

	public Circle getCircle() {
		return circle;
	}

	public void setCircle(Circle circle) {
		this.circle = circle;
	}

	public Square getSquare() {
		return square;
	}

	public void setSquare(Square square) {
		this.square = square;
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

	public AbstractRenderer getRenderer() {
		return renderer;
	}

	public void setRenderer(AbstractRenderer renderer) {
		this.renderer = renderer;
	}

	double getVoltageMax() {
		return voltageMax;
	}

	void setVoltageMax(double voltageMax) {
		this.voltageMax = voltageMax;
	}

	double getVoltageMin() {
		return voltageMin;
	}

	void setVoltageMin(double voltageMin) {
		this.voltageMin = voltageMin;
	}

	double getEyeIndicatorSize() {
		return eyeIndicatorSize;
	}

	void setEyeIndicatorSize(double eyeIndicatorSize) {
		this.eyeIndicatorSize = eyeIndicatorSize;
	}

	double getVoltageIndicatorSize() {
		return voltageIndicatorSize;
	}

	void setVoltageIndicatorSize(double voltageIndicatorSize) {
		this.voltageIndicatorSize = voltageIndicatorSize;
	}
}