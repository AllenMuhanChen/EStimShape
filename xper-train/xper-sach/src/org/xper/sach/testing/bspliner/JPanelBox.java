package org.xper.sach.testing.bspliner;

import java.awt.*;   
import javax.swing.*;   
import javax.swing.border.*;   
   
public class JPanelBox   
    extends JPanel {   
  public JPanelBox(Component component, String title) {   
    super(new BorderLayout());   
    add("Center", component);   
    setTitledBorder(title);   
  }   
   
  public JPanelBox(LayoutManager layout, String title) {   
    super(layout);   
    setTitledBorder(title);   
  }   
   
  public void setTitledBorder(String title) {   
    EtchedBorder etched = new EtchedBorder(EtchedBorder.LOWERED);   
    TitledBorder titled = new TitledBorder(etched, title);   
    super.setBorder(titled);   
  }   
}   