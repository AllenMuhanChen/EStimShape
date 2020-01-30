package org.xper.exception;

import org.springframework.core.NestedRuntimeException;

public class RuntimeIOException extends NestedRuntimeException {

	/**
	 * 
	 */
	private static final long serialVersionUID = 529865765815799625L;

	public RuntimeIOException (Throwable e) {
		super(e.getMessage(), e);
	}
	
	public RuntimeIOException (String msg) {
		super(msg);
	}
	
	public RuntimeIOException (String msg, Throwable e) {
		super(msg, e);
	}
}
