package org.xper.experiment.listener;

import org.xper.Dependency;

public class MessageDispatcherController implements ExperimentEventListener {
	@Dependency
	MessageDispatcher messageDispatcher;
	
	public void experimentStart(long timestamp) {
		messageDispatcher.start();
	}

	public void experimentStop(long timestamp) {
		messageDispatcher.stop();
	}

	public MessageDispatcher getMessageDispatcher() {
		return messageDispatcher;
	}

	public void setMessageDispatcher(MessageDispatcher messageDispatcher) {
		this.messageDispatcher = messageDispatcher;
	}

}
