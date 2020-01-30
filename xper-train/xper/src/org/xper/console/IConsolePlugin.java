package org.xper.console;

import java.awt.event.MouseEvent;
import java.awt.event.MouseWheelEvent;
import java.util.List;

import javax.swing.KeyStroke;

import org.xper.drawing.Context;

public interface IConsolePlugin {

	/**
	 * @param k
	 * @return
	 */
	void handleKeyStroke(KeyStroke k);

	/**
	 * Before ExperimentConsoleModel stopped.
	 */
	void stopPlugin();

	/**
	 * After ExperimentConsoleModel started.
	 */
	void startPlugin();

	void drawCanvas(Context context, String devId);

	void handleMouseMove(int x, int y);

	void handleMouseWheel(MouseWheelEvent e);

	String getPluginName();

	KeyStroke getToken();

	List<KeyStroke> getCommandKeys();

	String getPluginHelp();

	void handleMouseClicked(MouseEvent e);

}
