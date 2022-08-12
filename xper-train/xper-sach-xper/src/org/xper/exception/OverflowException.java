package org.xper.exception;

import org.springframework.core.NestedRuntimeException;

public class OverflowException extends NestedRuntimeException {
	/**
	 * 
	 */
	private static final long serialVersionUID = 1934150484966028507L;

	public OverflowException (Throwable e) {
		super(e.getMessage(), e);
	}
	
	public OverflowException (String msg) {
		super(msg);
	}
	
	public OverflowException (String msg, Throwable e) {
		super(msg, e);
	}
}
