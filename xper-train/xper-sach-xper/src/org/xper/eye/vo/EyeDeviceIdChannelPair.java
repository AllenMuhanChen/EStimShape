package org.xper.eye.vo;

public class EyeDeviceIdChannelPair {
	/**
	 * Device id
	 */
	String id;
	/**
	 * X or Y
	 */
	String channel;
	public String getChannel() {
		return channel;
	}
	public void setChannel(String channel) {
		this.channel = channel;
	}
	public String getId() {
		return id;
	}
	public void setId(String id) {
		this.id = id;
	}
	public EyeDeviceIdChannelPair() {
	}
	public EyeDeviceIdChannelPair(String id, String channel) {
		super();
		this.id = id;
		this.channel = channel;
	}
}
