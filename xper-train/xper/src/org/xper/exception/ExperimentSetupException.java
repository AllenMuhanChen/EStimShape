package org.xper.exception;

import org.springframework.core.NestedRuntimeException;

public class ExperimentSetupException extends NestedRuntimeException  {
	/**
	 * 
	 */
	private static final long serialVersionUID = 8625844557211806410L;

	public ExperimentSetupException (String msg) {
		super(msg);
	}
	
	public ExperimentSetupException (Throwable e) {
		super(e.getMessage(), e);
	}
	
	public ExperimentSetupException (String msg, Throwable e) {
		super(msg, e);
	}
}
