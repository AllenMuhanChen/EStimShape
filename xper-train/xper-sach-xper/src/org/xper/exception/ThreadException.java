package org.xper.exception;

import org.springframework.core.NestedRuntimeException;

public class ThreadException extends NestedRuntimeException {
	private static final long serialVersionUID = -1745206686322828062L;

	public ThreadException (Throwable e) {
		super(e.getMessage(), e);
	}
	
	public ThreadException (String msg) {
		super(msg);
	}
	
	public ThreadException (String msg, Throwable e) {
		super(msg, e);
	}
}
