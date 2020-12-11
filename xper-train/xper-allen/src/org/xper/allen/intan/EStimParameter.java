package org.xper.allen.intan;
/**
 * Designed to represent any parameter about the EStimSpec as a Name,Value pair, with the value being a String. Constructors convert other data types to String for value. 
 * @author Allen Chen
 *
 */
public class EStimParameter {
	String name;
	String value;
	
	public EStimParameter(String name, String value){
		this.name = name;
		this.value = value;
	}
	
	public EStimParameter(String name, Float value){
		this.name = name;
		this.value = Float.toString(value);
	}
	
	public EStimParameter(String name, Integer value){
		this.name = name;
		this.value = Integer.toString(value);
	}
	
	public EStimParameter(String name, Boolean value) {
		this.name = name;
		this.value = Boolean.toString(value);
	}
	
	public String getName() {
		return name;
	}
	public void setName(String name) {
		this.name = name;
	}
	public String getValue() {
		return value;
	}
	public void setValue(String value) {
		this.value = value;
	}
	
}
