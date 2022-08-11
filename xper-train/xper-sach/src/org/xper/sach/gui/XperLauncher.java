package org.xper.sach.gui;

import javax.swing.JOptionPane;
import javax.swing.SwingUtilities;
import javax.swing.UIManager;

import org.xper.sach.gui.model.DataSourceVO;
import org.xper.sach.gui.model.XperLauncherModel;
import org.xper.sach.gui.view.DataSourceDialog;
import org.xper.sach.gui.view.XperLauncherFrame;

public class XperLauncher {
	/**
	 * @param args
	 */
	public static void main(String[] args) {
		try {
			UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
		} catch (Exception e1) {}
		SwingUtilities.invokeLater(new Runnable() {
			public void run() {
				XperLauncherModel model = new XperLauncherModel();
				DataSourceVO initValue = model.getDataSourceVO();
				DataSourceDialog dialog = new DataSourceDialog(null, initValue);
				boolean done = false;
				while (!done) {
					DataSourceVO result = dialog.showDialog();
					if (result == null) {
						return;
					} else {
						String error = model.setAndTestDataSourceVO(result);
						if (error == null) {
							done = true;
						} else {
							JOptionPane.showMessageDialog(null, error, "Error", JOptionPane.ERROR_MESSAGE);
						}
					}
				}
				
				XperLauncherFrame launcherFrame = new XperLauncherFrame(model);
				launcherFrame.setVisible(true);
			}
		});
	}
}
