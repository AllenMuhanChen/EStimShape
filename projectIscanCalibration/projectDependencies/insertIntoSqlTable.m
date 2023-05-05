function insertIntoSqlTable(exdata,colnames,tableName,conn)
    exdata_table = cell2table(exdata,'VariableNames',colnames);
    insert(conn,tableName,colnames,exdata_table);

    id = exdata{2};
    if isnumeric(id) 
        id = num2str(id);
        disp(['inserted id = ' id]);
    end
end

