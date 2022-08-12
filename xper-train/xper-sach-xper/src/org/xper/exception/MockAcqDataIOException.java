package org.xper.exception;

import org.springframework.core.NestedRuntimeException;

public class MockAcqDataIOException extends NestedRuntimeException {
	/**
	 * 
	 */
	private static final long serialVersionUID = -6426259667710973671L;

	public MockAcqDataIOException(Throwable e) {
		super(e.getMessage(), e);
	}
	
	public MockAcqDataIOException (String msg) {
		super(msg);
	}
	
	public MockAcqDataIOException (String msg, Throwable e) {
		super(msg, e);
	}
}
