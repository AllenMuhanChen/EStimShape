function saveStimuliToDb(stimuli,mstickspec_all,colnames,tableName,conn)
    for l=1:2
        for s=1:size(stimuli,2)
            stim = stimuli{l,s};
            matspec = savejson('',stim);
            javaspec = formatAsXML_javaspec(stim);
            mstickspec = mstickspec_all{l,s};
            dataspec = formatAsXML_dataspec(stim.id);
            insertIntoSqlTable({stim.id.tstamp,stim.id.descId,javaspec,mstickspec,matspec,dataspec},colnames,tableName,conn);
        end
    end
end

