package org.xper.classic.vo;

import com.thoughtworks.xstream.XStream;

public class SlideEvent {
	int index;
	long timestamp;
	int frameCount;
	long taskId;
	
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
	
	public SlideEvent(int index, long timestamp, int frameCount, long taskId) {
		super();
		this.index = index;
		this.timestamp = timestamp;
		this.frameCount = frameCount;
		this.taskId = taskId;
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

	public long getTaskId() {
		return taskId;
	}

	public void setTaskId(long taskId) {
		this.taskId = taskId;
	}
}
