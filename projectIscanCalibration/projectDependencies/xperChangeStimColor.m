function xperChangeStimColor(fColor,bColor,conn)
    dataB = {num2str(bColor(1));num2str(bColor(2));num2str(bColor(3))};
    dataF = {num2str(fColor(1));num2str(fColor(2));num2str(fColor(3))};

%     setdbprefs('FetchInBatches','no');
    
    updateSqlTable(dataB,{'val'},'SystemVar',{'where name = ''xper_stim_color_background'' and arr_ind = 0';...
                                            'where name = ''xper_stim_color_background'' and arr_ind = 1';...
                                            'where name = ''xper_stim_color_background'' and arr_ind = 2'},conn);
    
    updateSqlTable(dataF,{'val'},'SystemVar',{'where name = ''xper_stim_color_foreground'' and arr_ind = 0'...
                                            'where name = ''xper_stim_color_foreground'' and arr_ind = 1'...
                                            'where name = ''xper_stim_color_foreground'' and arr_ind = 2'},conn);
end

