package org.xper.eye.listener;

import org.xper.eye.EyeSampler;

public interface EyeSamplerEventListener {
	public void sample (EyeSampler sampler, long timestamp);
	public void start ();
	public void stop ();
}
