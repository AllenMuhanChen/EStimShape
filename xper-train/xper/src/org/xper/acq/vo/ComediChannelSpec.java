package org.xper.acq.vo;

public class ComediChannelSpec {
	public static String AREF_DIFF = "diff";
	public static String AREF_GROUND = "ground";
	public static String AREF_COMMON = "common";
	public static String AREF_OTHER = "other";
	
	short channel;
	double minValue;
	double maxValue;
	String aref;
	
	public double getMinValue() {
		return minValue;
	}
	public void setMinValue(double minValue) {
		this.minValue = minValue;
	}
	public double getMaxValue() {
		return maxValue;
	}
	public void setMaxValue(double maxValue) {
		this.maxValue = maxValue;
	}
	public String getAref() {
		return aref;
	}
	public void setAref(String aref) {
		this.aref = aref;
	}
	public short getChannel() {
		return channel;
	}
	public void setChannel(short channel) {
		this.channel = channel;
	}
}
