package org.xper.rfplot;

import java.awt.event.KeyEvent;
import java.awt.event.KeyListener;
import java.awt.event.MouseEvent;
import java.awt.event.MouseListener;
import java.awt.event.MouseMotionListener;
import java.awt.event.MouseWheelListener;
import java.util.List;

import javax.swing.JPanel;
import javax.swing.KeyStroke;

public abstract class RFPlotControl implements KeyListener, MouseListener, MouseMotionListener, MouseWheelListener {
	/**
	 * @return UI elements to control the specification of the stimulus
	 */
	public JPanel getUI() {
		return null;
	}
	/**
	 * 
	 * @return specification of the stimulus
	 */
	public String getSpec(){
		return null;
	}
	/**
	 * 
	 * @return command keys for this control to receive future mouse events and non-command key events
	 */
	public List<KeyStroke> commandStroke() {
		return null;
	}
	
	public void mouseDragged(MouseEvent e) {
	}
	
	public void mouseMoved(MouseEvent e) {
	}
	
	public void mouseClicked(MouseEvent e) {
	}
	
	public void mouseEntered(MouseEvent e) {
	}
	
	public void mouseExited(MouseEvent e) {
	}
	
	public void mousePressed(MouseEvent e) {
	}
	
	public void mouseReleased(MouseEvent e) {
	}
	
	public void keyPressed(KeyEvent e) {
	}
	
	public void keyReleased(KeyEvent e) {
	}
	
	public void keyTyped(KeyEvent e) {
	}
}
