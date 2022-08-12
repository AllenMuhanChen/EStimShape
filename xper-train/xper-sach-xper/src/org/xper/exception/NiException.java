package org.xper.exception;

import org.springframework.core.NestedRuntimeException;

public class NiException extends NestedRuntimeException {
	/**
	 * 
	 */
	private static final long serialVersionUID = 7957147681144455808L;

	public NiException (String msg) {
		super(msg);
	}
	
	public NiException (Throwable e) {
		super(e.getMessage(), e);
	}
	
	public NiException (String msg, Throwable e) {
		super(msg, e);
	}
}
