package org.xper.exception;

import org.springframework.core.NestedRuntimeException;

public class InvalidAcqDataException extends NestedRuntimeException {

	/**
	 * 
	 */
	private static final long serialVersionUID = -9019361844045832587L;

	public InvalidAcqDataException (String msg) {
		super(msg);
	}
	
	public InvalidAcqDataException (Throwable e) {
		super(e.getMessage(), e);
	}
	
	public InvalidAcqDataException (String msg, Throwable e) {
		super(msg, e);
	}
}
