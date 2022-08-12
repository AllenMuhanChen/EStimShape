package org.xper.exception;

import org.springframework.core.NestedRuntimeException;

public class RemoteException extends NestedRuntimeException {
	private static final long serialVersionUID = -2930487320283220851L;

	public RemoteException (Throwable e) {
		super(e.getMessage(), e);
	}
	
	public RemoteException (String msg) {
		super(msg);
	}
	
	public RemoteException (String msg, Throwable e) {
		super(msg, e);
	}
}
