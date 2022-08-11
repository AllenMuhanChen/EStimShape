function val = SystemVar(conn, name, varargin)
if isempty(varargin)
    arr_ind = 0;
else
    arr_ind = varargin{1};
end 
sqlQuery = 'SELECT val FROM SystemVar WHERE name="'+name+'" AND arr_ind='+ num2str(arr_ind);
val = fetch(conn,sqlQuery);
val = table2array(val); 

if ~isnan(str2double(val))
    val = str2double(val);
else
    val = char(val);
end 
end 
