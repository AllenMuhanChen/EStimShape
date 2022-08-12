package org.xper.mockxper.plugin;

import java.io.BufferedReader;
import java.io.InputStreamReader;

import org.xper.mockxper.MockSpikeGenerator;

public class ManualInputSpikeGenerator implements MockSpikeGenerator {

	public double getSpikeRate(long taskId) {
		boolean done = false;
		double rate = -1.0;
		while (!done) {
			System.out.println();
			System.out.println("Enter spike rate for " + taskId + ": ");
			BufferedReader in = new BufferedReader(new InputStreamReader(
					System.in));
			try {
				rate = Double.parseDouble(in.readLine());
				System.out.println("Got number " + rate);
				if (rate <= 0) {
					System.out.println("Invalid number. Try again.");
				} else {
					done = true;
				}
				
			} catch (Exception e) {
				System.out.println("Invalid number. Try again.");
			}
		}
		return rate;
	}

}
