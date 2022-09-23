package org.xper.app.rfplot;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.config.AcqConfig;
import org.xper.rfplot.RFPlotConfig;
import org.xper.rfplot.RFPlotTaskDataSource;
import org.xper.util.FileUtil;

public class RFPlotServer {
    public static void main(String[] args) {
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("rfplot.config_class", RFPlotConfig.class));

        RFPlotTaskDataSource server = context.getBean(RFPlotTaskDataSource.class);

        server.run();

    }
}
