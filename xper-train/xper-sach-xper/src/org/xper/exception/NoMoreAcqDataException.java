package org.xper.exception;

import org.springframework.core.NestedRuntimeException;

public class NoMoreAcqDataException extends NestedRuntimeException {

	/**
	 * 
	 */
	private static final long serialVersionUID = -9019361844045832587L;

	public NoMoreAcqDataException (String msg) {
		super(msg);
	}
	
	public NoMoreAcqDataException (Throwable e) {
		super(e.getMessage(), e);
	}
	
	public NoMoreAcqDataException (String msg, Throwable e) {
		super(msg, e);
	}
}
