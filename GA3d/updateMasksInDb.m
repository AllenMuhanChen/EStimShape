function updateMasksInDb(stimuli,conn)
    for l=1:2
        for s=1:size(stimuli,2)
            stim = stimuli{l,s};
            matspec = savejson('',stim);
            javaspec = formatAsXML_javaspec(stim);
            
            updateSqlTable({javaspec,matspec},{'javaspec','matspec'},'StimObjData',['where descId = ''' stim.id.descId ''''],conn)
        end
    end
end