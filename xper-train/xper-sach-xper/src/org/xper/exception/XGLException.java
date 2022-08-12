package org.xper.exception;

import org.springframework.core.NestedRuntimeException;

public class XGLException extends NestedRuntimeException {
	/**
	 * 
	 */
	private static final long serialVersionUID = -1409808116659392456L;

	public XGLException (Throwable e) {
		super(e.getMessage(), e);
	}
	
	public XGLException (String msg) {
		super(msg);
	}
	
	public XGLException (String msg, Throwable e) {
		super(msg, e);
	}
}
