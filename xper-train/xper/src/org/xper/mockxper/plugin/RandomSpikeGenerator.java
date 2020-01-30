package org.xper.mockxper.plugin;

import java.util.Random;

import org.xper.Dependency;
import org.xper.mockxper.MockSpikeGenerator;

public class RandomSpikeGenerator implements MockSpikeGenerator {
	Random rand = new Random();
	
	@Dependency
	double min;
	@Dependency
	double max;
	
	public void setMax(double max) {
		this.max = max;
	}

	public void setMin(double min) {
		this.min = min;
	}

	public double getSpikeRate(long taskId) {
		return (max-min) * rand.nextDouble() + min;
	}

}
