package org.xper.rds;

import java.awt.event.KeyEvent;
import java.awt.event.MouseEvent;
import java.awt.event.MouseWheelEvent;
import java.util.ArrayList;
import java.util.List;

import javax.swing.KeyStroke;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.console.IConsolePlugin;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.drawing.object.FixationPoint;
import org.xper.util.GuiUtil;

public class RdsConsolePlugin implements IConsolePlugin {
	static Logger logger = Logger.getLogger(RdsConsolePlugin.class);
	
	@Dependency
	float maxFixationSize = 100; // mm
	@Dependency
	float minFixationSize = 5;
	@Dependency
	float fixationSizeStep = 1;
	@Dependency
	float maxDisplacement = 10; // degree
	@Dependency
	float minDisplacement = 0;
	@Dependency
	float displacementStep = 0.1f;
	@Dependency
	float fixationColorStep = 0.02f;
	@Dependency
	float initDimFactor = 0.3f;
	@Dependency
	RGBColor backgroundColor;
	@Dependency
	RGBColor fixationColor;
	@Dependency
	List<Coordinates2D> fixationDirections = new ArrayList<Coordinates2D>(){
		private static final long serialVersionUID = 1L;
		{
			add(new Coordinates2D(0,0));
			add(new Coordinates2D(1, 1));
			add(new Coordinates2D(-1,1));
			add(new Coordinates2D(-1,-1));
			add(new Coordinates2D(1,-1));
		}
	};
	@Dependency
	RdsControlClient rdsControlClient;
	@Dependency
	FixationPoint consoleFixationPoint;
	
	float fixationSize;
	float displacement;
	float red;
	float green;
	float blue;
	int direction;
	
	KeyStroke rdsToken = KeyStroke.getKeyStroke(KeyEvent.VK_F2, 0);
	
	final int directionKey = KeyEvent.VK_1;
	final int colorKey = KeyEvent.VK_2;
	final int displacementKey = KeyEvent.VK_3;
	final int sizeKey = KeyEvent.VK_4;
	
	int keyState = directionKey;
	
	@Override
	public String getPluginHelp() {
		StringBuffer buf = new StringBuffer();
		buf.append("<html>");
		buf.append("<strong>" + getPluginName() + " commands</strong> <br>");
		buf.append("<strong>" + GuiUtil.getKeyText(directionKey) + "</strong>: direction <br>");
		buf.append("<strong>" + GuiUtil.getKeyText(colorKey) + "</strong>: color <br>");
		buf.append("<strong>" + GuiUtil.getKeyText(displacementKey) + "</strong>: displacement <br>");
		buf.append("<strong>" + GuiUtil.getKeyText(sizeKey) + "</strong>: size <br>");
		buf.append("scroll mouse wheel or click left/right button to change value");
		buf.append("</html>");
		return buf.toString();
	}
	
	@Override
	public List<KeyStroke> getCommandKeys() {
		List<KeyStroke> keys = new ArrayList<KeyStroke>();
		keys.add(KeyStroke.getKeyStroke(directionKey, 0));
		keys.add(KeyStroke.getKeyStroke(colorKey, 0));
		keys.add(KeyStroke.getKeyStroke(displacementKey, 0));
		keys.add(KeyStroke.getKeyStroke(sizeKey, 0));
		return keys;
	}

	@Override
	public void handleKeyStroke(KeyStroke k) {
		int keyCode = k.getKeyCode();
		switch (keyCode) {
		case directionKey:
		case colorKey:
		case displacementKey:
		case sizeKey: 
			keyState = keyCode;
			if (logger.isDebugEnabled()) {
				logger.debug(GuiUtil.keyStroke2String(k));
			}
			break;
		}
	}

	@Override
	public void startPlugin() {
		fixationSize = minFixationSize;
		displacement = 1;
		direction = 0;
		red = fixationColor.getRed() * initDimFactor;
		green = fixationColor.getGreen() * initDimFactor;
		blue = fixationColor.getBlue() * initDimFactor;
	}

	@Override
	public void stopPlugin() {
		rdsControlClient.stop();
	}

	@Override
	public void drawCanvas(Context context, String devId) {
	}

	@Override
	public void handleMouseMove(int x, int y) {
	}
	
	float changeColor (float c, float bg, float fg, float step) {
		float r = c + step;
		if (r < bg) r = bg;
		else if (r > fg) r = fg;
		return r;
	}
	
	void setCoordinate (int direction, float displacement) {
		float x = (float)(fixationDirections.get(direction).getX()) * displacement;
		float y = (float)(fixationDirections.get(direction).getY()) * displacement;
		consoleFixationPoint.setFixationPosition(new Coordinates2D(x, y));
		rdsControlClient.setCoordinate(x, y);
	}
	
	@Override
	public void handleMouseClicked(MouseEvent e) {
		int b = e.getButton();
		if (logger.isDebugEnabled()) {
			logger.debug("Mouse button: " + b);
		}
		if (b == MouseEvent.BUTTON1) {
			changeFixation(1);
		} else if (b == MouseEvent.BUTTON3){
			changeFixation(-1);
		}
	}
	
	void changeFixation(int d) {
		switch (keyState) {
		case directionKey:
			direction += Math.signum(d);
			if (direction < 0) direction = 0;
			else if (direction >= fixationDirections.size()) direction = fixationDirections.size() - 1;
			if (logger.isDebugEnabled()) {
				logger.debug("Direction: " + direction);
			}
			setCoordinate(direction, displacement);
			break;
		case colorKey:
			float colorStep = Math.signum(d) * fixationColorStep;
			red = changeColor(red, backgroundColor.getRed(), fixationColor.getRed(), colorStep);
			green = changeColor(green, backgroundColor.getGreen(), fixationColor.getGreen(), colorStep);
			blue = changeColor(blue, backgroundColor.getBlue(), fixationColor.getBlue(), colorStep);
			if (logger.isDebugEnabled()) {
				logger.debug("Color: " + red + ", " + green + ", " + blue);
			}
			consoleFixationPoint.setColor(new RGBColor(red, green, blue));
			rdsControlClient.setColor(red, green, blue);
			break;
		case displacementKey:
			displacement += Math.signum(d) * displacementStep;
			if (displacement > maxDisplacement) {
				displacement = maxDisplacement;
			} else if (displacement < minDisplacement) {
				displacement = minDisplacement;
			}
			if (logger.isDebugEnabled()) {
				logger.debug("Displacement: " + displacement);
			}
			setCoordinate(direction, displacement);
			break;
		case sizeKey:
			fixationSize += Math.signum(d) * fixationSizeStep;
			if (fixationSize > maxFixationSize) {
				fixationSize = maxFixationSize;
			} else if (fixationSize < minFixationSize) {
				fixationSize = minFixationSize;
			}
			if (logger.isDebugEnabled()) {
				logger.debug("Fixation Size: " + fixationSize);
			}
			consoleFixationPoint.setSize(fixationSize);
			rdsControlClient.setSize(fixationSize);
			break;
		}
	}

	@Override
	public void handleMouseWheel(MouseWheelEvent e) {
		int w = e.getWheelRotation();
		if (logger.isDebugEnabled()) {
			logger.debug("Mouse wheel: " + w);
		}
		changeFixation(w);
	}

	@Override
	public String getPluginName() {
		return "RDS mode";
	}

	@Override
	public KeyStroke getToken() {
		return rdsToken;
	}

	public float getMaxFixationSize() {
		return maxFixationSize;
	}

	public void setMaxFixationSize(float maxFixationSize) {
		this.maxFixationSize = maxFixationSize;
	}

	public float getMinFixationSize() {
		return minFixationSize;
	}

	public void setMinFixationSize(float minFixationSize) {
		this.minFixationSize = minFixationSize;
	}

	public RdsControlClient getRdsControlClient() {
		return rdsControlClient;
	}

	public void setRdsControlClient(RdsControlClient rdsControlClient) {
		this.rdsControlClient = rdsControlClient;
	}

	public RGBColor getBackgroundColor() {
		return backgroundColor;
	}

	public void setBackgroundColor(RGBColor backgroundColor) {
		this.backgroundColor = backgroundColor;
	}

	public RGBColor getFixationColor() {
		return fixationColor;
	}

	public void setFixationColor(RGBColor fixationColor) {
		this.fixationColor = fixationColor;
	}

	public float getInitDimFactor() {
		return initDimFactor;
	}

	public void setInitDimFactor(float initDimFactor) {
		this.initDimFactor = initDimFactor;
	}

	public FixationPoint getConsoleFixationPoint() {
		return consoleFixationPoint;
	}

	public void setConsoleFixationPoint(FixationPoint consoleFixationPoint) {
		this.consoleFixationPoint = consoleFixationPoint;
	}

}
