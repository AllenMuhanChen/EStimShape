package org.xper.exception;

import org.springframework.core.NestedRuntimeException;

public class XmlDocInvalidFormatException extends NestedRuntimeException {
	/**
	 * 
	 */
	private static final long serialVersionUID = 5453152422610025180L;

	public XmlDocInvalidFormatException (Throwable e) {
		super(e.getMessage(), e);
	}
	
	public XmlDocInvalidFormatException (String msg) {
		super(msg);
	}
	
	public XmlDocInvalidFormatException (String msg, Throwable e) {
		super(msg, e);
	}
}
