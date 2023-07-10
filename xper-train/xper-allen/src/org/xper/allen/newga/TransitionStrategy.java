package org.xper.allen.newga;

public interface TransitionStrategy {
    boolean shouldTransition(long lineageId);
}