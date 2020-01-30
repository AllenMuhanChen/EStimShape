package org.xper.exception;

import org.springframework.core.NestedRuntimeException;

public class AcqException extends NestedRuntimeException {
	/**
	 * 
	 */
	private static final long serialVersionUID = 6248049835718500000L;

	public AcqException (String msg) {
		super(msg);
	}
	
	public AcqException (Throwable e) {
		super(e.getMessage(), e);
	}
	
	public AcqException (String msg, Throwable e) {
		super(msg, e);
	}
}
