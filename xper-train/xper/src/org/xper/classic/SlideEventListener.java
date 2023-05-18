package org.xper.classic;

public interface SlideEventListener {
	public void slideOn (int index, long timestamp, long taskId);
	public void slideOff (int index, long timestamp, int frameCount, long taskId);
}