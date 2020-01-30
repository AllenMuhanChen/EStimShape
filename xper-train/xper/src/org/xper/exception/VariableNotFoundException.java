package org.xper.exception;

import org.springframework.core.NestedRuntimeException;

public class VariableNotFoundException extends NestedRuntimeException {
	/**
	 * 
	 */
	private static final long serialVersionUID = -6327716545505873230L;

	public VariableNotFoundException (Throwable e) {
		super(e.getMessage(), e);
	}
	
	public VariableNotFoundException (String msg) {
		super(msg);
	}
	
	public VariableNotFoundException (String msg, Throwable e) {
		super(msg, e);
	}
}
