function conn = DBConnect

datasource = "v1microstim";
username = "xper_rw";
password = "up2nite";
conn = database(datasource, username, password);

end 