package org.xper.classic.vo;

import com.thoughtworks.xstream.XStream;

public class SlideEvent {
	int index;
	long timestamp;
	int frameCount;
	
	static XStream xstream = new XStream();

	static {
		xstream.alias("SlideEvent", SlideEvent.class);
	}
	
	public static SlideEvent fromXml (String xml) {
		return (SlideEvent)xstream.fromXML(xml);
	}
	
	public static String toXml (SlideEvent msg) {
		return xstream.toXML(msg);
	}
	
	public SlideEvent(int index, long timestamp, int frameCount) {
		super();
		this.index = index;
		this.timestamp = timestamp;
		this.frameCount = frameCount;
	}
	public int getFrameCount() {
		return frameCount;
	}
	public void setFrameCount(int frameCount) {
		this.frameCount = frameCount;
	}
	public int getIndex() {
		return index;
	}
	public void setIndex(int index) {
		this.index = index;
	}
	public long getTimestamp() {
		return timestamp;
	}
	public void setTimestamp(long timestamp) {
		this.timestamp = timestamp;
	}
}
