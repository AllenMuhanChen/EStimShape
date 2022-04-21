package org.xper.allen.drawing.composition.noisy;

public class Pair<T1, T2> {
	T1 Key;
	T2 Value;
	
	public Pair(T1 key, T2 value) {
		super();
		Key = key;
		Value = value;
	}

	public T1 getKey() {
		return Key;
	}

	public void setKey(T1 key) {
		Key = key;
	}

	public T2 getValue() {
		return Value;
	}

	public void setValue(T2 value) {
		Value = value;
	}
	
	



}
