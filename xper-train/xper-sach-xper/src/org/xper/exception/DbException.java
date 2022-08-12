package org.xper.exception;

import org.springframework.core.NestedRuntimeException;

public class DbException extends NestedRuntimeException {	
	/**
	 * 
	 */
	private static final long serialVersionUID = -7454754210813077402L;

	public DbException (String msg) {
		super(msg);
	}
	
	public DbException (Throwable e) {
		super(e.getMessage(), e);
	}
	
	public DbException (String msg, Throwable e) {
		super(msg, e);
	}
}
