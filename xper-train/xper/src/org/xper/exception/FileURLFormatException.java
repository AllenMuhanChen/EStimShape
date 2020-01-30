package org.xper.exception;

import org.springframework.core.NestedRuntimeException;

public class FileURLFormatException extends NestedRuntimeException {
	/**
	 * 
	 */
	private static final long serialVersionUID = -1566807515657824028L;

	public FileURLFormatException (Throwable e) {
		super(e.getMessage(), e);
	}
	
	public FileURLFormatException (String msg) {
		super(msg);
	}
	
	public FileURLFormatException (String msg, Throwable e) {
		super(msg, e);
	}
}
