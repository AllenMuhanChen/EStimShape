package org.xper.sach.gui.exception;

public class ConfigException extends RuntimeException {
	/**
	 * 
	 */
	private static final long serialVersionUID = 1030511195437634323L;

	public ConfigException (String msg) {
		super(msg);
	}
	
	public ConfigException (Throwable e) {
		super(e);
	}
	
	public ConfigException (String msg, Throwable e) {
		super(msg, e);
	}
}
