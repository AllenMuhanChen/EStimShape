package org.xper.exception;

import org.springframework.core.NestedRuntimeException;

public class ComediException extends NestedRuntimeException {
	/**
	 * 
	 */
	private static final long serialVersionUID = -6997124849459465217L;

	public ComediException (String msg) {
		super(msg);
	}
	
	public ComediException (Throwable e) {
		super(e.getMessage(), e);
	}
	
	public ComediException (String msg, Throwable e) {
		super(msg, e);
	}
}
