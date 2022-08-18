function updateSqlTable(data,colname,tableName,whereclause,conn)
    % data and colname should be cell arrays
    update(conn,tableName,colname,data,whereclause)
end

