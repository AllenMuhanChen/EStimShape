package org.xper.sach.gui.view;

import java.awt.Color;
import java.awt.Component;

import javax.swing.JTable;
import javax.swing.table.DefaultTableCellRenderer;

import org.xper.util.DateUtil;

public class AcqSessionTableCellRenderer extends DefaultTableCellRenderer {

	private static final long serialVersionUID = -4353568364494941817L;

	@Override
	public Component getTableCellRendererComponent(JTable table, Object value, boolean isSelected, boolean hasFocus, int row, int column) {
		super.getTableCellRendererComponent(table, value, isSelected, hasFocus,
				row, column);
		if (!isSelected) {
			if (row % 2 == 0) {
				setBackground(new Color(0.9f, 0.9f, 1f));
			} else {
				setBackground(new Color(1f, 1f, 1f));
			}
		}
		setToolTipText(DateUtil.timestampToDateString((Long)value));
		return this;
	}
	
	

}
