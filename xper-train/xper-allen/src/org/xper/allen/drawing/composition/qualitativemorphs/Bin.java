package org.xper.allen.drawing.composition.qualitativemorphs;

public class Bin <T> {
	public T min;
	public T max;
	
	public Bin(T min, T max){
		this.min = min;
		this.max = max;
	}
}
