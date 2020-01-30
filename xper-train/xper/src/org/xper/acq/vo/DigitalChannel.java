package org.xper.acq.vo;

import org.xper.acq.player.DigitalPlayer;


public class DigitalChannel {
	public static final int ONE = 1;
	public static final int ZERO = 0;
	
	public static final int UP = 2;
	public static final int DOWN = -2; 
	
	public static final int PULSE_CENTER = 4;
	public static final int PULSE_UP = 8;
	public static final int PULSE_DOWN = -8;
	
	public enum EdgeType {Up, Down, Center};
	
	public static DigitalPlayer.Type stringToDataPlayerType (String type) {
		if (type.equalsIgnoreCase("digital")) return DigitalPlayer.Type.Full;
		if (type.equalsIgnoreCase("half_digital")) return DigitalPlayer.Type.Half;
		if (type.equalsIgnoreCase("quad_center_digital")) return DigitalPlayer.Type.QuadCenter;
		if (type.equalsIgnoreCase("quad_up_digital")) return DigitalPlayer.Type.QuadUp;
		if (type.equalsIgnoreCase("quad_down_digital")) return DigitalPlayer.Type.QuadDown;
		return DigitalPlayer.Type.Invalid;
	}
}
